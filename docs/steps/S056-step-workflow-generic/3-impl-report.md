```
Step: S056 — The step workflow names no repo: Yantra's specifics move to its settings
Doc: impl-report
Author: Coder (Opus)
Date: 25-10-2026
```

# S056 — implementation report

**Result.** The step skill, the five agents and the two READMEs name no repo now. Yantra's values
are in a new `## Step workflow` section of `.claude/CLAUDE.md`. The step index and queue moved to
`docs/steps/INDEX.md`, the roadmap index to `docs/roadmap/INDEX.md`, and the step tools read
`INDEX.md`. All § 5 checks ran; their output is below. Tooling tests: 263 passed. No question for
the user.

## 1. What was built

- **The index move** (§ 1.3): `docs/steps/INDEX.md` holds the README's `## Index` and
  `## Queued (not yet briefed)` word for word, under a three-line head. `docs/roadmap/INDEX.md`
  holds the roadmap README's `## Index`. The READMEs keep only the conventions.
- **The step tools** read `docs/steps/INDEX.md` (`step_facts.py`: `gather()`, `SHARED_DOCS`, the
  `parse_index` docstring). `step_check.py` says "INDEX row" in its messages. The tests follow.
- **The settings** (§ 1.2): `.claude/CLAUDE.md` § Step workflow. First the old *Step workflow*
  bullet of § Yantra Specifics, moved as prose lines (with the two `INDEX.md` paths added). Then
  nine entries in the `- **Entry**: value` form: *Unit tests*, *Browser tests*, *Plan and domain
  docs*, *Standards*, *Self-check, repo items*, *Shared code*, *Device checks*, *Roadmap mock-ups*,
  *Use on the floor*.
- **The generic text** (§ 1.1, § 1.4): each Yantra line in the eight prose files became the
  generic text of § 1.1 with a pointer "(settings: *Entry*)". The index references name
  `docs/steps/INDEX.md` or `docs/roadmap/INDEX.md` (§ 1.3 list); git's "index" is unchanged.
- **The README's new section** `## The repo's settings and index`: the entries and what each holds,
  the `none` consequences, the stop message for a repo without the section, and the shape of
  `INDEX.md` that `parse_index` reads (BR1-03).

## 2. How it works

- An agent reads `.claude/CLAUDE.md` as project instructions, so the `## Step workflow` section is
  always in its context. Where a generic file needs a value, it says "(settings: *Entry*)", and the
  agent reads that bullet. Example: the coder's "run the repo's command for all suites (settings:
  *Unit tests*)" reads, for Yantra, `tooling/run-tests.bat`.
- The long Yantra rules stay where they were (§ Yantra Specifics, *Browser tests (S024)*,
  *Standards and best practice*, *RBAC deviation*, *DB may not exist*, *Worker*, *Migrations*).
  The settings point at them by name and hold only the values the generic files used to quote
  (decision 4 of the brief).
- Each agent file's first lines now say where the settings are. The skill says what to do when
  the section is missing (the README's stop message).
- `step_facts.gather()` opens `docs/steps/INDEX.md`. `parse_index` reads by shape, so the head
  lines of `INDEX.md` change nothing. `SHARED_DOCS` lists `INDEX.md` and `device-checks.md`; the
  README is no longer a shared doc, so a change to it is claimed by the step that names it.

## 3. Files touched

| File | Change |
|---|---|
| `docs/steps/INDEX.md` | new: the index and the queue, moved word for word; S056's row summary corrected and its status set (D9) |
| `docs/roadmap/INDEX.md` | new: the roadmap index, moved |
| `docs/steps/README.md` | conventions made generic; `## Index` and `## Queued` removed; new `## The repo's settings and index` |
| `docs/roadmap/README.md` | conventions made generic; `## Index` removed |
| `.claude/CLAUDE.md` | new `## Step workflow` section; the *Step workflow* bullet of § Yantra Specifics moved into it |
| `.claude/skills/step/SKILL.md` | generic; settings pointers; `INDEX.md` paths; self-check item 16 |
| `.claude/agents/coder.md` | generic; settings pointers; `INDEX.md` paths |
| `.claude/agents/code-reviewer.md` | generic; settings pointers |
| `.claude/agents/brief-reviewer.md` | generic; settings pointers; `INDEX.md` path; UX list: the Yantra lines moved, "the repo's own points" added |
| `.claude/agents/advisor.md` | description and first line generic |
| `.claude/agents/roadmapper.md` | generic; settings pointers; `INDEX.md` paths; template `by <user>` |
| `tooling/steps/step_facts.py` | reads `INDEX.md`; `SHARED_DOCS`; `readme_status` → `index_status` (D3) |
| `tooling/steps/step_check.py` | "INDEX row" messages; `check_stage_matches_readme` → `check_stage_matches_index` (D3) |
| `tooling/tests/test_step_facts.py` | fixture `README` → `INDEX`; the asserted "has no INDEX row"; renamed function and class |
| `docs/steps/S056-step-workflow-generic/1-brief.md` | Status `In code review` |

16 files with this report: 3 new, 13 changed. Line endings kept (CRLF or LF as each file had); no
lone CR in any of them (checked byte by byte after the last edit). The backslash paths
(`tooling\release-tests.bat`, `docs\roadmap\R0N-mockups`, the `\_` of the SQL in CLAUDE.md) are
intact: the same lines as before.

## 4. Decisions taken

- **D1 — Illustrative examples off the word list stay.** Examples that are not values the workflow
  depends on are unchanged: the README's header example `Step: S001 — Basic masters`,
  `docs/steps/S001-basic-masters/` and the commit example; the skill's "UI on the masters pattern"
  and "(the pure core of PM triggers, KPIs)"; "the badge, the timeline line, the times card"; the
  roadmapper's user story and `01-todays-jobs.html`, "Technician A"; the roadmap README's
  "e.g. preventive maintenance"; the code reviewer's `ApiError`, `btn-sm`. They illustrate a rule
  and do not change it. Alternative rejected: make each generic, which loses the concrete picture
  for no change in behaviour. **To confirm at gate B** (the brief says "names no … domain").
- **D2 — Row g: the example commands moved to the settings instead of being dropped.** The example
  backend command, the e2e examples and `frontend/src/views/` are in *Unit tests*, *Browser tests*
  and *Roadmap mock-ups*. So no backticked token is dropped at all (token check below).
  The parallel-steps "never" list (SKILL.md, via *Shared code*) now also names `useFormModal.js` and
  the auth store, which the old parenthesis did not list; the settings entry holds the one list
  (added in fix round 1, CR1-02).
- **D3 — Renamed identifiers** for one term: `readme_status` → `index_status`,
  `check_stage_matches_readme` → `check_stage_matches_index`, `TestStageMatchesReadme` →
  `TestStageMatchesIndex`, the test fixture `README` → `INDEX`. Internal names only; no caller
  outside `tooling/steps/` and its tests (grep).
- **D4 — The moved *Step workflow* bullet is prose at the section's top**, not an entry: § 1.2
  says "its first lines", and a parser of `- **Entry**:` bullets skips it. The old bullet is gone
  from § Yantra Specifics, with no pointer, so `CLAUDE.md` has one place of that name (BR1-04).
- **D5 — The `none` column** gives the three consequences the brief names (browser tests,
  standards, named person); the other entries say "the generic text only". No new rule.
- **D6 — Self-check item 12's "(S021 CR1-01)" moved to the settings**, as row b says. It is an
  evidence tag, which BR1-07 keeps elsewhere; row b is the more specific rule. The generic item
  says "(provenance: settings, *Self-check, repo items*)".
- **D7 — Self-check item 4 (identity paths: "`active`, login name, role, site") is unchanged**:
  no word-list word, and "site" reads as a general scope.
- **D8 — Self-check gets item 16** "The repo's own items (settings: *Self-check, repo items*)",
  as row b's "a last item". Items 1–15 keep their numbers, so the settings cite them by number.
- **D9 — S056's own row in `INDEX.md`**: its summary still described the design before U2 ("the
  conventions to `.claude/step-workflow.md`; the README keeps the index"). I wrote what was built
  and set the status `In code review`. Every other row moved word for word.
- **D10 — "e2e" became "browser" / "browser-test"** in the generic text (it is on the word list);
  the stats description says "browser-test cost".
- **D11 — Values the settings hold that the old lines did not quote**: *Plan and domain docs*
  names `docs/schema.md` (the roadmapper's line named it); *Browser tests* names
  `scratch/e2e-run.lock` (from § Browser tests) and `tooling/run-e2e-tests.bat --level=…`. All are
  facts from the old files or `CLAUDE.md`; no rule is new.
- **D12 — Token check by set difference per file** (every backticked token in the old file that is
  missing from the new one), not by `git diff --word-diff=porcelain`. It is stricter: a token
  counts as gone only when no occurrence is left, and it does not depend on how git aligns the
  words.

## 5. Not done, deferred or assumed

- S057's part is not touched: `step_stats.py`'s browser-test parsing, `brief_facts.py`'s
  `SEARCH_DIRS`, the `.bat` wrappers, the lift list and `sync_common.py`.
- § 6 Q2 confirmed: `grep -rn README tooling/` finds only `step_facts.py`, `step_check.py` and
  `test_step_facts.py`; no tool parses the conventions.
- The past step files keep "README § Index" (out of scope, BR2-04).
- The S056 row went from "Approved, coding" straight to "In code review", the stage the coder sets
  at hand-over.

## 6. The § 5 checks

### 6.1 Order of work and the tools

1. Captured "before" at 82997ee + S056's step files: the four tools, the word grep, the outline,
   copies of the eight prose files and `CLAUDE.md` (session scratchpad).
2. Moved the index and switched the tools; `tooling/run-tooling-tests.bat`
   (`YANTRA_TEST_RUN=s056c1`): **263 passed**. Diff of the tool outputs then (before any prose):
   - `step-check.bat`: `S056: README row says "Approved, coding" …` became
     `S056: INDEX row says "Approved, coding" …`; `(shared step docs changed: docs/steps/README.md)`
     became `… docs/steps/INDEX.md`. The other new lines were this step's own uncommitted files
     ("no step claims it (10)"), and a `grep.exe.stackdump` my crashed grep left in the repo root,
     which I deleted.
   - `step-ls.bat all`: the same two changes, the same unclaimed files, and
     `working tree: M docs/steps/README.md` under three uncommitted steps whose impl reports name
     the README (the README is no longer a shared doc; BR1-02's "checked and found consistent"
     list says this is right).
   - `step-stats.bat`: only the build time and S056's own live numbers (minutes, a token share).
   - `step-feedback.bat`: no difference.
3. Then the prose. Final run, after this report: § 6.6.

### 6.2 The word list, after

The § 5 pattern (case-insensitive, the eight prose files): **251 lines before, 28 after.** What is
left, and why:

| Hits | Why it stays |
|---|---|
| `KLA` in 22 lines (SKILL.md 51, 111, 248, 334, 352, 369, 377, 435, 443, 465, 487, 502, 539, 674, 683; coder.md 161; code-reviewer.md 183; brief-reviewer.md 167; advisor.md 83; roadmapper.md 62; README.md 45; roadmap README.md 6) | provenance tags "(…, by KLA)" (§ 1.1 row 1) |
| `blank` (SKILL.md 510 "a blank line", 614 "blank: queued"; code-reviewer.md 128 "not blank or a 403") | the English word, not the composable's `blank` |
| `Normal` (SKILL.md 199 "normalised names") | inside another word |
| `Basic` (README.md 30 `docs/steps/S001-basic-masters/`, 55 `Step: S001 — Basic masters`) | the README's format examples (D1) |

No stack word of row k is hit: the `frontend/` and `backend/` hits moved with row g's paths, and
Bootstrap (code-reviewer.md, `modal-dialog-scrollable`), `uv run`, `node -e` and PowerShell
(advisor.md, SKILL.md item 1) are not on the list; they stay, as row k says.

The full output:

```
.claude/skills/step/SKILL.md:51: [KLA] (deferred) ones (25-10-2026, by KLA).
.claude/skills/step/SKILL.md:111: [KLA] rule, 24-10-2026, by KLA). The user's request is the approval.
.claude/skills/step/SKILL.md:199: [Normal] Cover actor = target, normalised names, inactive people, and reused
.claude/skills/step/SKILL.md:248: [KLA] - **Advice** (25-10-2026, by KLA). Before writing a claim or a design
.claude/skills/step/SKILL.md:334: [KLA] - **Housekeeping: the docs pass** (standing rule, 24-10-2026, by KLA).
.claude/skills/step/SKILL.md:352: [KLA] - **Browser runs at their level** (standing rule, 25-10-2026, by KLA;
.claude/skills/step/SKILL.md:369: [KLA] 24-10-2026, by KLA: asking the user about each minor finding cost more
.claude/skills/step/SKILL.md:377: [KLA] - **Async verify review** (standing rule, 25-10-2026, by KLA). When that
.claude/skills/step/SKILL.md:435: [KLA] KLA); conventions in `docs/roadmap/README.md`.
.claude/skills/step/SKILL.md:443: [KLA] - **The deck** (25-10-2026, by KLA): when the roadmapper is done, render its mock-ups with
.claude/skills/step/SKILL.md:465: [KLA] and read-only experiments (25-10-2026, by KLA; first run: S053's power
.claude/skills/step/SKILL.md:487: [KLA] Every agent ends its file with `## Feedback` (25-10-2026, by KLA; README § Folder and files): at
.claude/skills/step/SKILL.md:502: [KLA] Standing rule (24-10-2026, by KLA): each step gets its own commit, while the
.claude/skills/step/SKILL.md:510: [blank] commit message (one line, the `S00N:` prefix, then a blank line and the
.claude/skills/step/SKILL.md:539: [KLA] An option (24-10-2026, by KLA), not the default: a second coder works at the
.claude/skills/step/SKILL.md:614: [blank] - blank: queued or `Dropped`.
.claude/skills/step/SKILL.md:674: [KLA] - **Agents change nothing outside the repo** (standing rule, 25-10-2026, by KLA; an
.claude/skills/step/SKILL.md:683: [KLA] - **Recommend clearing the context** (standing rule, 25-10-2026, by KLA).
.claude/agents/coder.md:161: [KLA] End your file with `## Feedback` (25-10-2026, by KLA): what in the workflow, the tools or the
.claude/agents/code-reviewer.md:128: [blank] *Use on the floor*) rendered, not blank or a 403.
.claude/agents/code-reviewer.md:183: [KLA] End your file with `## Feedback` (25-10-2026, by KLA): what in the workflow, the tools or the
.claude/agents/brief-reviewer.md:167: [KLA] End your file with `## Feedback` (25-10-2026, by KLA): what in the workflow, the tools or the
.claude/agents/advisor.md:83: [KLA] End your file with `## Feedback` (25-10-2026, by KLA): what in the workflow, the tools or the
.claude/agents/roadmapper.md:62: [KLA] (25-10-2026, by KLA). You write its material; the orchestrator renders and publishes it.
docs/steps/README.md:30: [Basic] One folder per step: `docs/steps/S001-basic-masters/`. The slug is kebab-case
docs/steps/README.md:45: [KLA] **Feedback** (25-10-2026, by KLA). Every file an agent writes — advice, brief review, impl report,
docs/steps/README.md:55: [Basic] Step: S001 — Basic masters
docs/roadmap/README.md:6: [KLA] **gate R**; each item becomes a step only when the user takes it up (25-10-2026, by KLA). The
```

### 6.3 Token conservation

Script: the scratchpad's `tokens.py`. For each prose file, every backticked token of the old file
that no longer appears in the new one, and where it is now. **0 tokens without a home; 0 dropped
on purpose** (rows g, i, j, l drop only plain words: "Yantra" in the descriptions and first lines,
"KLA" in the templates, "the user is learning maintenance practice" — none is backticked; row g's
examples moved to the settings, D2). The `INDEX.md` lines are the README's index rows, moved.

```
.claude/skills/step/SKILL.md: `--level=basic` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `--level=full` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `@device` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/skills/step/SKILL.md: `@smoke` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/skills/step/SKILL.md: `FormModal.vue` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `SITE_SCOPED` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `YANTRA_TEST_RUN` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `_PRECONDITIONS` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/skills/step/SKILL.md: `_TABLES` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `api.js` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `blank` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `conftest.py` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `db_down` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `desktop-chromium` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `device-checks.md` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/skills/step/SKILL.md: `docs/Plan.MD` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `docs/steps/device-checks.md` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `e2e/support/` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `expectDialogFits` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `local_db.py` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/skills/step/SKILL.md: `masters.py` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `open(seed)` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `phone-chromium` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `s021c1` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `s021cr2` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `scratch/` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `screens.spec.js` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `test_migration_*` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `test_role_matrix` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `tickets.py` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `tooling/release-tests.bat` -> CLAUDE.md § Step workflow
.claude/skills/step/SKILL.md: `tooling/run-e2e-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `--level=basic` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `--level=full` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `--project` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `@device` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/coder.md: `@smoke` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/coder.md: `FormModal.vue` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `YANTRA_TEST_RUN` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `YANTRA_TEST_RUN=s021cr3 tooling/run-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `api.js` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `desktop-chromium` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `dev` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/coder.md: `device-checks.md` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/coder.md: `docs/steps/device-checks.md` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `e2e/screens.spec.js` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `e2e/support/` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `expectDialogFits` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `expectFieldMessage` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `frontend/` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `frontend/e2e/` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `npx vite build` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `phone-chromium` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `phone-webkit` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/coder.md: `release` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/coder.md: `screens.spec.js` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `set E2E_LANES=1` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `test("…", { tag: "@device" }, async …)` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `tooling/release-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `tooling/run-e2e-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `tooling/run-e2e-tests.bat --level=…` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `tooling/run-frontend-tests.bat <file>` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `tooling/run-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/coder.md: `useFormModal.js` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `--level=basic` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `--level=full` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `--project` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `@device` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/code-reviewer.md: `@smoke` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/code-reviewer.md: `YANTRA_TEST_RUN` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `YANTRA_TEST_RUN=s021cr3 tooling/run-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `desktop-chromium` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `dev` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/code-reviewer.md: `docs/steps/device-checks.md` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `e2e/screens.spec.js` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `expectDialogFits` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `frontend/` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `npx vite build` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `phone-chromium` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `release` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
.claude/agents/code-reviewer.md: `screens.spec.js` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `tooling/release-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `tooling/run-e2e-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/code-reviewer.md: `tooling/run-tests.bat` -> CLAUDE.md § Step workflow
.claude/agents/brief-reviewer.md: `docs/Maintenance-Philosophy.md` -> CLAUDE.md § Step workflow
.claude/agents/brief-reviewer.md: `docs/Plan.MD` -> CLAUDE.md § Step workflow
.claude/agents/brief-reviewer.md: `docs/Plant-Facts.md` -> CLAUDE.md § Step workflow
.claude/agents/roadmapper.md: `../../../frontend/node_modules/bootstrap/dist/css/bootstrap.min.css` -> CLAUDE.md § Step workflow
.claude/agents/roadmapper.md: `../../../frontend/src/assets/main.css` -> CLAUDE.md § Step workflow
.claude/agents/roadmapper.md: `docs/Maintenance-Philosophy.md` -> CLAUDE.md § Step workflow
.claude/agents/roadmapper.md: `docs/Plan.MD` -> CLAUDE.md § Step workflow
.claude/agents/roadmapper.md: `docs/Plant-Facts.md` -> CLAUDE.md § Step workflow
.claude/agents/roadmapper.md: `docs/schema.md` -> CLAUDE.md § Step workflow
.claude/agents/roadmapper.md: `frontend/src/views/` -> CLAUDE.md § Step workflow
docs/steps/README.md: `--level=basic` -> CLAUDE.md § Step workflow
docs/steps/README.md: `--level=full` -> CLAUDE.md § Step workflow
docs/steps/README.md: `.claude/step-workflow.md` -> docs/steps/INDEX.md
docs/steps/README.md: `/e/<code>` -> docs/steps/INDEX.md
docs/steps/README.md: `/pre-flight` -> docs/steps/INDEX.md
docs/steps/README.md: `@device` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/steps/README.md: `@smoke` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/steps/README.md: `BUILDKIT_SBOM_SCAN_STAGE` -> docs/steps/INDEX.md
docs/steps/README.md: `Claude-Session` -> docs/steps/INDEX.md
docs/steps/README.md: `Co-Authored-By` -> docs/steps/INDEX.md
docs/steps/README.md: `Done (committed abc123; checks: 6 auto, 2 done by IT Admin, 1 skipped — iPhone)` -> CLAUDE.md § Step workflow
docs/steps/README.md: `E2E_LANES` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/steps/README.md: `IN (…)` -> docs/steps/INDEX.md
docs/steps/README.md: `RPP` -> docs/steps/INDEX.md
docs/steps/README.md: `TEST_CMD` -> docs/steps/INDEX.md
docs/steps/README.md: `TK-` -> docs/steps/INDEX.md
docs/steps/README.md: `_PRECONDITIONS` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/steps/README.md: `accessible_unit_ids` -> docs/steps/INDEX.md
docs/steps/README.md: `claude/component-unit-hierarchy-tfa3gg` -> docs/steps/INDEX.md
docs/steps/README.md: `device-checks.md` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/steps/README.md: `docker build --sbom=true` -> docs/steps/INDEX.md
docs/steps/README.md: `equipment.model_id` -> docs/steps/INDEX.md
docs/steps/README.md: `equipment:read` -> docs/steps/INDEX.md
docs/steps/README.md: `equipment_property_values` -> docs/steps/INDEX.md
docs/steps/README.md: `erp_spanner.py backup` -> docs/steps/INDEX.md
docs/steps/README.md: `frontend/e2e/` -> CLAUDE.md § Step workflow
docs/steps/README.md: `latest` -> docs/steps/INDEX.md
docs/steps/README.md: `local_db.py` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/steps/README.md: `main` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/steps/README.md: `meter_readings` -> docs/steps/INDEX.md
docs/steps/README.md: `page.route` -> docs/steps/INDEX.md
docs/steps/README.md: `people.email` -> docs/steps/INDEX.md
docs/steps/README.md: `people:assign_technicians` -> docs/steps/INDEX.md
docs/steps/README.md: `phone-webkit` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/steps/README.md: `refs/notes/preflight` -> docs/steps/INDEX.md
docs/steps/README.md: `release.py` -> docs/steps/INDEX.md
docs/steps/README.md: `requirements.txt` -> docs/steps/INDEX.md
docs/steps/README.md: `run-server` -> docs/steps/INDEX.md
docs/steps/README.md: `s009-code.patch` -> docs/steps/INDEX.md
docs/steps/README.md: `sbom/` -> docs/steps/INDEX.md
docs/steps/README.md: `screens.spec.js` -> CLAUDE.md § Step workflow
docs/steps/README.md: `smtw-common` -> docs/steps/INDEX.md
docs/steps/README.md: `ticket:backdate` -> docs/steps/INDEX.md
docs/steps/README.md: `tooling/common/preflight.py` -> docs/steps/INDEX.md
docs/steps/README.md: `tooling/machine-check.bat` -> docs/steps/INDEX.md
docs/steps/README.md: `tooling/release-tests.bat` -> CLAUDE.md § Step workflow
docs/steps/README.md: `tooling/run-e2e-tests.bat` -> CLAUDE.md § Step workflow
docs/steps/README.md: `user_units` -> docs/steps/INDEX.md
docs/roadmap/README.md: `Plan.MD` -> CLAUDE.md § Step workflow, docs/steps/INDEX.md
docs/roadmap/README.md: `docs/Plan.MD` -> CLAUDE.md § Step workflow
0 token(s) not found in a home
```

### 6.4 The outline

`grep -n '^#'` of the eight files, before and after, line numbers stripped, `diff`:

```
69,70c69
< ## Index
< ## Queued (not yet briefed)
---
> ## The repo's settings and index
76d74
< ## Index
```

Lines 69–70 are `docs/steps/README.md` (the two index sections moved, the new section added); line
76 is `docs/roadmap/README.md` (its index moved). No heading lost or reordered.

### 6.5 The equivalence table

Every changed hunk of the eight files whose old text holds a word of the § 5 list, from a
`difflib` comparison of the before copy with the file now (the scratchpad's `equiv.py`). "Yantra's
value now" is the settings entry the new text points at; "— (row …)" marks a word dropped on
purpose; `INDEX.md` marks the moved index. Rows 1–42 are the skill, 43–56 the coder, 57–67 the
code reviewer, 68–77 the brief reviewer, 78–79 the advisor, 80–89 the roadmapper, 90–102 the steps
README, 103–107 the roadmap README.

| # | File:line (old) | Old text | New generic text | Yantra's value now |
|---|---|---|---|---|
| 1 | `.claude/skills/step/SKILL.md:3` | description: Orchestrate Yantra's step workflow (docs/steps) from one terminal — plan a step and loop it through the Fable brief reviewer, then implement it with the coder subagent (Sonnet, or Opus when complex) and loop it through the Opus code reviewer, stopping only at the user's gates. Use when the user says /step, "run S00N", "plan/implement/review step …", asks to drive the step loop, or asks which steps are open (`/step ls`). | description: Orchestrate the step workflow (docs/steps) from one terminal — plan a step and loop it through the Fable brief reviewer, then implement it with the coder subagent (Sonnet, or Opus when complex) and loop it through the Opus code reviewer, stopping only at the user's gates. Use when the user says /step, "run S00N", "plan/implement/review step …", asks to drive the step loop, or asks which steps are open (`/step ls`). | — (row i: dropped on purpose) |
| 2 | `.claude/skills/step/SKILL.md:57` | and majors, time, tokens and e2e cost per step and per role, from the step | and majors, time, tokens and browser-test cost per step and per role, from the step | *Browser tests* ("browser" for "e2e") |
| 3 | `.claude/skills/step/SKILL.md:108` | - it fixes behaviour against what a brief, Plan.MD or the docs already say, | - it fixes behaviour against what a brief, the plan doc or the docs already say, | *Plan and domain docs* ("the plan doc") |
| 4 | `.claude/skills/step/SKILL.md:111` | - no permissions: RBAC keys, roles, `SITE_SCOPED`, login, the network gate; | - no permissions: RBAC keys, roles, login, and the repo's permission tables and gates (settings: *Self-check, repo items*); | *Self-check, repo items* |
| 5 | `.claude/skills/step/SKILL.md:114` | - no security-sensitive code: uploads, file serving, secrets, push or email addresses; | - no security-sensitive code: uploads, file serving, secrets, and the security-sensitive code the repo names (settings: *Self-check, repo items*); | *Self-check, repo items* |
| 6 | `.claude/skills/step/SKILL.md:126` | (*red, then green*), runs the full unit suites, and makes targeted e2e runs when a screen changed (the whole e2e suite at Normal once at the | (*red, then green*), runs the full unit suites, and makes targeted browser runs when a screen changed (the whole-suite run once at the | *Browser tests* ("browser" for "e2e") |
| 7 | `.claude/skills/step/SKILL.md:139` | 1. **Write the brief.** The ID is the next free `S0NN` in the README index. - Write `1-brief.md` with status `Draft` and its `Track`, then add the index row. A light brief uses the short template. - Split the checks a person would make into **Automated** (an e2e browser | 1. **Write the brief.** The ID is the next free `S0NN` in `docs/steps/INDEX.md`. - Write `1-brief.md` with status `Draft` and its `Track`, then add its row in `docs/steps/INDEX.md`. A light brief uses the short template. - Split the checks a person would make into **Automated** (a browser | *Browser tests* ("browser" for "e2e") |
| 8 | `.claude/skills/step/SKILL.md:144` | a dialog fits a phone) and **On a real device** (camera, paper, the iPhone keyboard, a real Keycloak login), each device check with its account, network and where (dev server on KLA's laptop, production on the TEST machine, or either). Mark the ones that matter as **important** (README | a dialog fits a phone) and **On a real device** (the checks a browser engine cannot judge; settings: *Device checks*), each device check with its account, network and where (the machines the settings name: *Device checks*). Mark the ones that matter as **important** (README | *Device checks* |
| 9 | `.claude/skills/step/SKILL.md:149` | - Follow CLAUDE-COMMON "Show the plan before building" and the Yantra rule on standards. | - Follow CLAUDE-COMMON "Show the plan before building" and the repo's rule on standards, if it has one (settings: *Standards*). | *Standards* |
| 10 | `.claude/skills/step/SKILL.md:177` | `uv run python` or `node -e` check for library behaviour (QR version, Pillow, Bootstrap, urllib parsing). Open the file for "the API shows X". Grep the devops repo, compose and cron for a task said not to | `uv run python` or `node -e` check for library behaviour (examples: settings, *Self-check, repo items*). Open the file for "the API shows X". Grep the places the settings name for a task said not to | *Self-check, repo items* |
| 11 | `.claude/skills/step/SKILL.md:183` | the LOCK ORDER notes in `tickets.py` and `masters.py`. Decide from the | the repo's lock notes (settings: *Self-check, repo items*). Decide from the | *Self-check, repo items* |
| 12 | `.claude/skills/step/SKILL.md:185` | after an earlier plain read (REPEATABLE READ). A counter or "same | after an earlier plain read (the database's isolation level: settings, *Self-check, repo items*). A counter or "same | *Self-check, repo items* |
| 13 | `.claude/skills/step/SKILL.md:187` | 3. **Permissions**: the exact key of every route and button, held at which site (`SITE_SCOPED`); reads behind a senior key scoped to the sites where it is held; no login or personal data beyond its key. | 3. **Permissions**: the exact key of every route and button, and where it is checked (settings: *Self-check, repo items*); reads behind a senior key scoped as the settings say; no login or personal data beyond its key. | *Self-check, repo items* |
| 14 | `.claude/skills/step/SKILL.md:196` | name — always check `test_role_matrix`, `conftest.py` `_TABLES`, the `db_down` fixture and the `test_migration_*` upgrade tests. For each | name — always check the repo's always-check tests (settings: *Self-check, repo items*). For each | *Self-check, repo items* |
| 15 | `.claude/skills/step/SKILL.md:199` | state. The e2e specs (targeted or full) and the S024 conventions (allowed 400s, set-up by API, `expectDialogFits`, the open-dialog wait, per-lane databases). | state. The browser specs (targeted or full) and the repo's browser-test conventions (settings: *Browser tests*). | *Browser tests* |
| 16 | `.claude/skills/step/SKILL.md:208` | 8. **Plan.MD and earlier steps**: nothing decided there is re-asked or | 8. **The plan doc and earlier steps**: nothing decided there is re-asked or | *Plan and domain docs* ("the plan doc") |
| 17 | `.claude/skills/step/SKILL.md:213` | migration number, the lock notes, the e2e conventions and new README | migration number, the lock notes, the browser-test conventions and new README | *Browser tests* ("browser" for "e2e") |
| 18 | `.claude/skills/step/SKILL.md:216` | `_PRECONDITIONS` against production's real rows; the settings dicts | the repo's migration guards (settings: *Self-check, repo items*) against production's real rows; the settings dicts | *Self-check, repo items* |
| 19 | `.claude/skills/step/SKILL.md:221` | 11. **The database down and the worker** (CLAUDE.md): what each new hook, route and task does when the DB is unreachable. For a worker task, | 11. **A dependency down, and background tasks** (settings: *Self-check, repo items*): what each new hook, route and task does when a dependency is down. For a background task, | *Self-check,          repo items* |
| 20 | `.claude/skills/step/SKILL.md:228` | contract (what `blank` returns, what `open(seed)` does), the fields | contract (settings: *Self-check, repo items*), the fields | *Self-check, repo items* |
| 21 | `.claude/skills/step/SKILL.md:280` | decisions in `docs/Plan.MD`. | decisions in the plan doc (settings: *Plan and domain docs*). | *Plan and domain docs* |
| 22 | `.claude/skills/step/SKILL.md:314` | run name (`YANTRA_TEST_RUN`, e.g. `s021c1`, `s021cr2`), so agents running tests at the same time never share a database. | run name (the repo's test run name variable, settings: *Unit tests*), so agents running tests at the same time never share a database. | *Unit tests* |
| 23 | `.claude/skills/step/SKILL.md:343` | levels S047). `tooling/run-e2e-tests.bat` has three levels: **Basic** (`--level=basic`: the `@smoke` journeys and `screens.spec.js` on `phone-chromium`, about 2 minutes), **Normal** (no flag: every test on `phone-chromium`, the `@device` tests on `desktop-chromium`) and **Full** (`--level=full`: every test on the Android phone, the `@device` tests on desktop and the iPhone in its container). The coder makes targeted runs (Normal with spec files) as often as it needs, and may run Basic for a quick whole-app check. It runs the whole suite at Normal once, when the coding is done, | levels S047), where the repo has browser tests. The repo's browser tests have a quick whole-app run, a whole-suite run and a release level (settings: *Browser tests*). The coder makes targeted runs (the whole-suite level with spec files) as often as it needs, and may make the quick whole-app run. It makes the whole-suite run once, when the coding is done, | *Browser tests* |
| 24 | `.claude/skills/step/SKILL.md:355` | tell it so in the spawn prompt. The Full level runs only in the release (`tooling/release-tests.bat` runs it after the unit suites) and when KLA asks. | tell it so in the spawn prompt. The release level runs only in the release (the repo's release tests run it after the unit suites) and when the user asks (settings: *Browser tests*). | *Browser tests* |
| 25 | `.claude/skills/step/SKILL.md:402` | - the e2e result (`tooling/run-e2e-tests.bat`: the coder's whole-suite run at Normal at the end of coding, the targeted runs of the fix rounds, and the results) and the `[auto]` checks as | - the browser-test result (the coder's whole-suite run at the end of coding, the targeted runs of the fix rounds, and the results) and the `[auto]` checks as | *Browser tests* ("browser" for "e2e") |
| 26 | `.claude/skills/step/SKILL.md:406` | rows are in `docs/steps/device-checks.md` for the user or the named person (today IT Admin). The user decides which checks are which and may skip | rows are in the repo's device-check list for the user or the named person (settings: *Device checks*). The user decides which checks are which and may skip | *Device checks* |
| 27 | `.claude/skills/step/SKILL.md:417` | is `[auto]` (a passing e2e run), ticked by the user or for the named person, | is `[auto]` (a passing browser run), ticked by the user or for the named person, | *Browser tests* ("browser" for "e2e") |
| 28 | `.claude/skills/step/SKILL.md:420` | report and in the row's *Done* column of `device-checks.md`; a skip as | report and in the row's *Done* column of the device-check list; a skip as | *Device checks* |
| 29 | `.claude/skills/step/SKILL.md:422` | e.g. `Done (committed abc123; checks: 6 auto, 2 done by IT Admin, 1 skipped — iPhone)`. Never tick a check yourself. | e.g. `Done (committed abc123; checks: 6 auto, 2 done by <name>, 1 skipped — <reason>)` (settings: *Device checks*). Never tick a check yourself. | *Device checks* |
| 30 | `.claude/skills/step/SKILL.md:430` | - **Spawn** it with the feature, why KLA wants it now, and anything he said about scope or order. It reads Plan.MD, the domain docs, the steps done and the code, and writes only `docs/roadmap/R0N-<slug>.md`. | - **Spawn** it with the feature, why the user wants it now, and anything the user said about scope or order. It reads the plan doc, the domain docs (settings: *Plan and domain docs*), the steps done and the code, and writes only `docs/roadmap/R0N-<slug>.md`. | *Plan and domain docs* |
| 31 | `.claude/skills/step/SKILL.md:434` | and only when KLA takes an item up (`/step plan R0N.n`). Add the roadmap's index row in `docs/roadmap/README.md` yourself. | and only when the user takes an item up (`/step plan R0N.n`). Add the roadmap's index row in `docs/roadmap/INDEX.md` yourself. | — (row 1 / row j: "the user") |
| 32 | `.claude/skills/step/SKILL.md:440` | `slides`, then the Slides type; the images go up as the artifact's assets). KLA can view it on | `slides`, then the Slides type; the images go up as the artifact's assets). The user can view it on | — (row 1 / row j: "the user") |
| 33 | `.claude/skills/step/SKILL.md:442` | deck after a re-plan. The roadmap file stays the record; the deck is how KLA reviews it. | deck after a re-plan. The roadmap file stays the record; the deck is how the user reviews it. | — (row 1 / row j: "the user") |
| 34 | `.claude/skills/step/SKILL.md:445` | heading. KLA approves; record his answers in the roadmap (Status `Approved …`), and the lasting decisions in Plan.MD. | heading. The user approves; record the answers in the roadmap (Status `Approved …`), and the lasting decisions in the plan doc. | — (row 1 / row j: "the user") |
| 35 | `.claude/skills/step/SKILL.md:539` | - two steps that both add a migration (`local_db.py` and the schema docs always conflict); - two steps that touch the same screen or shared frontend code (the router, the nav, `FormModal.vue`, `api.js`, `e2e/support/`), or the same entries of `conftest.py`; | - two steps that both add a migration (the repo's migrations module and the schema docs always conflict; settings: *Shared code*); - two steps that touch the same screen or the repo's shared frontend code, or the same entries of the shared test fixtures (settings: *Shared code*); | *Shared code* |
| 36 | `.claude/skills/step/SKILL.md:554` | Browser tests still take turns: the e2e lock is per machine (in the main working folder's `scratch/`, so a worktree's run waits for it too, S047). | Browser tests still take turns: the browser-test lock is per machine, so a worktree's run waits for it too (settings: *Browser tests*). | *Browser tests* |
| 37 | `.claude/skills/step/SKILL.md:557` | not the README index, not `device-checks.md`. It writes the changes it | not `docs/steps/INDEX.md`, not the device-check list. It writes the changes it | *Device checks* |
| 38 | `.claude/skills/step/SKILL.md:569` | 4. **test the joined code**: the backend suite and the targeted e2e specs | 4. **test the joined code**: the backend suite and the targeted browser specs | *Browser tests* ("browser" for "e2e") |
| 39 | `.claude/skills/step/SKILL.md:587` | items with a step ID, the shared docs changed (README, `device-checks.md`), the | items with a step ID, the shared docs changed (`INDEX.md`, the device-check list), the | *Device checks* |
| 40 | `.claude/skills/step/SKILL.md:646` | 7. `device-checks.md`'s *Done* column and the impl report's ticks disagree; | 7. the device-check list's *Done* column and the impl report's ticks disagree; | *Device checks* |
| 41 | `.claude/skills/step/SKILL.md:683` | an impl report or Plan.MD, and every gate shown is in the step files; | an impl report or the plan doc, and every gate shown is in the step files; | *Plan and domain docs* ("the plan doc") |
| 42 | `.claude/skills/step/SKILL.md:696` | touched, because the user is learning maintenance practice. | touched, where the repo has a standards rule (settings: *Standards*). | *Standards* |
| 43 | `.claude/agents/coder.md:3` | description: Implements an approved Yantra step brief (or an approved amendment, or a code-review fix round) and writes/updates 3-impl-report.md. Used by the /step orchestrator. Default model Sonnet; the orchestrator passes model opus for complex steps. | description: Implements an approved step brief (or an approved amendment, or a code-review fix round) and writes/updates 3-impl-report.md. Used by the /step orchestrator. Default model Sonnet; the orchestrator passes model opus for complex steps. | — (row i: dropped on purpose) |
| 44 | `.claude/agents/coder.md:7` | You are the **coder** in Yantra's step workflow. Before anything else, read | You are the **coder** in the step workflow. Before anything else, read | — (row i: dropped on purpose) |
| 45 | `.claude/agents/coder.md:51` | there, edit no shared step doc (the README index, `device-checks.md`), and | there, edit no shared step doc (`docs/steps/INDEX.md`, the device-check list), and | *Device checks* |
| 46 | `.claude/agents/coder.md:81` | - **Your own test run name** (22-10-2026): set `YANTRA_TEST_RUN` to a short | - **Your own test run name** (22-10-2026): set the repo's test run name variable (settings: *Unit tests*) to a short | *Unit tests* |
| 47 | `.claude/agents/coder.md:83` | run, e.g. `YANTRA_TEST_RUN=s021cr3 tooling/run-tests.bat` (the orchestrator | run (the orchestrator | *Unit tests* |
| 48 | `.claude/agents/coder.md:91` | e.g. `tooling/run-backend-tests.bat tests/test_tickets_core.py tests/test_ticket_work_api.py` (pytest arguments pass through), and `tooling/run-frontend-tests.bat <file>`; the targeted e2e specs (below). - Once, when the code is done: `tooling/run-tests.bat` (it needs the dev DB up), and `npx vite build` in `frontend/` when the frontend changed. A red | with the repo's per-suite commands (settings: *Unit tests*); the targeted browser specs (below). - Once, when the code is done: the repo's command for all suites, and its build check when the frontend changed (settings: *Unit tests*). A red | *Unit tests* |
| 49 | `.claude/agents/coder.md:100` | - **Browser tests** (S024; `docs/steps/README.md` § Manual checks): - write an e2e test (`frontend/e2e/`, Playwright) for each *Automated* check of the brief, asserting what the user would see; call `expectDialogFits` on every dialog a flow test opens; | - **Browser tests** (S024; `docs/steps/README.md` § Manual checks), where the repo has them (settings: *Browser tests*): - write a browser test for each *Automated* check of the brief, asserting what the user would see, by the repo's test conventions (settings: *Browser tests*); | *Browser tests* |
| 50 | `.claude/agents/coder.md:107` | lane, on the logic device: `set E2E_LANES=1` then `tooling/run-e2e-tests.bat e2e/<spec>.spec.js --project=phone-chromium -g "S0NN"` (the other projects are `desktop-chromium` and `phone-webkit`; a `--project` you | lane, on the logic device (the command: settings, *Browser tests*; the other device projects are there too; a project you | *Browser tests* |
| 51 | `.claude/agents/coder.md:112` | - **the levels** (S047; `tooling/run-e2e-tests.bat --level=…`): **Basic** (`--level=basic`) runs the `@smoke` tests, the four journeys and `screens.spec.js`, on `phone-chromium`, about 2 minutes; **Normal** (no flag, the default) runs every test on `phone-chromium` and the `@device` tests on `desktop-chromium`; **Full** (`--level=full`) runs every test on the Android phone and the `@device` tests on desktop and the iPhone; - **tag a new test** `@device` (`test("…", { tag: "@device" }, async …)`) only when its purpose is a layout check (its title names fits, in view, on screen, scrolls to, no sideways scroll, above or below; or its main assertion is a geometry), or it runs only on, or asserts differently on, a project other than `phone-chromium`. A logic test stays untagged, also when it calls `expectDialogFits` or `expectFieldMessage`: the Android phone checks those in every flow, and another device checks a dialog only through a `@device` test; - run the e2e tests whenever the frontend or an API the screens use | - **the levels** (S047; settings: *Browser tests*): the quick whole-app run, the whole-suite run (the default) and the release level, each with its devices; - **tag a new test** with the repo's layout tag only by its rule (settings: *Browser tests*): a layout check by purpose, or a test that runs only on, or asserts differently on, a device other than the logic device. A logic test stays untagged; - run the browser tests whenever the frontend or an API the screens use | *Browser tests* |
| 52 | `.claude/agents/coder.md:128` | - **targeted** runs (Normal with spec files) as often as you need: the spec files of the screens and APIs the step changed (the spec-to-step map in `.claude/CLAUDE.md` § SMTW-Review) plus `e2e/screens.spec.js`, e.g. `tooling/run-e2e-tests.bat e2e/tickets-work.spec.js e2e/screens.spec.js`. You may run Basic when you want a quick whole-app check; - **the whole suite at Normal** (`tooling/run-e2e-tests.bat`, no spec file) **once**, when the coding is done. Run it again only with a | - **targeted** runs as often as you need: the spec files of the screens and APIs the step changed (the repo's spec-to-step map) plus the specs the settings always add (settings: *Browser tests*). You may make the quick whole-app run when you want a check of the whole app; - **the whole-suite run** (settings: *Browser tests*) **once**, when the coding is done. Run it again only with a | *Browser tests* |
| 53 | `.claude/agents/coder.md:137` | specs, or you then changed shared frontend code: `FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store, `e2e/support/`); | specs, or you then changed the repo's shared frontend files, settings: *Shared code*); | *Shared code* |
| 54 | `.claude/agents/coder.md:141` | - never the Full level: it runs only in the release (`tooling/release-tests.bat`) and when KLA asks. | - never the release level: it runs only in the release (the repo's release tests) and when the user asks. | — (row 1 / row j: "the user") |
| 55 | `.claude/agents/coder.md:149` | - append the brief's *On a real device* checks as rows to `docs/steps/device-checks.md` (what to do and see, account, network, | - append the brief's *On a real device* checks as rows to the repo's device-check list (settings: *Device checks*; what to do and see, account, network, | *Device checks* |
| 56 | `.claude/agents/coder.md:204` | `- [auto] … — <test file>::<test name>` once the e2e run passed; real-device | `- [auto] … — <test file>::<test name>` once the browser run passed; real-device | *Browser tests* ("browser" for "e2e") |
| 57 | `.claude/agents/code-reviewer.md:3` | description: Reviews a Yantra step's implementation (working-tree diff) against its approved brief and amendments, runs the tests, and writes the next 4-code-review-rN.md. Used by the /step orchestrator; never edits code. | description: Reviews a step's implementation (working-tree diff) against its approved brief and amendments, runs the tests, and writes the next 4-code-review-rN.md. Used by the /step orchestrator; never edits code. | — (row i: dropped on purpose) |
| 58 | `.claude/agents/code-reviewer.md:8` | You are the **code reviewer** in Yantra's step workflow. The conventions are in | You are the **code reviewer** in the step workflow. The conventions are in | — (row i: dropped on purpose) |
| 59 | `.claude/agents/code-reviewer.md:30` | - **Your own test run name** (22-10-2026): set `YANTRA_TEST_RUN` to a short | - **Your own test run name** (22-10-2026): set the repo's test run name variable (settings: *Unit tests*) to a short | *Unit tests* |
| 60 | `.claude/agents/code-reviewer.md:32` | run, e.g. `YANTRA_TEST_RUN=s021cr3 tooling/run-tests.bat` (the orchestrator | run (the orchestrator | *Unit tests* |
| 61 | `.claude/agents/code-reviewer.md:42` | - **Run the tests yourself.** Run `tooling/run-tests.bat`, and `npx vite build` in `frontend/` if the frontend changed. Record the real result. A red suite is a `blocker`. | - **Run the tests yourself.** Run the repo's command for all suites, and its build check if the frontend changed (settings: *Unit tests*). Record the real result. A red suite is a `blocker`. | *Unit tests* |
| 62 | `.claude/agents/code-reviewer.md:46` | runs the e2e specs and records the counts in the impl report. Don't repeat | runs the browser specs and records the counts in the impl report. Don't repeat | *Browser tests* ("browser" for "e2e") |
| 63 | `.claude/agents/code-reviewer.md:50` | - **Which browser tests a step needs** (S024; levels S047), when the frontend or an API the screens use changed. `tooling/run-e2e-tests.bat` has three levels: Basic (`--level=basic`, the `@smoke` journeys and `screens.spec.js` on `phone-chromium`), Normal (no flag: every test on `phone-chromium`, the `@device` tests on `desktop-chromium`) and Full (`--level=full`: every test on the Android phone, the `@device` tests on desktop and the iPhone). The coder runs **targeted** runs (Normal with the spec files of the screens and APIs the step changed, from the spec-to-step map in `.claude/CLAUDE.md` § SMTW-Review, plus `e2e/screens.spec.js`) as often as it needs, and **the whole suite at Normal once** when the coding | - **Which browser tests a step needs** (S024; levels S047), when the repo has browser tests and the frontend or an API the screens use changed. The repo's browser tests have a quick whole-app run, a whole-suite run and a release level (settings: *Browser tests*). The coder runs **targeted** runs (the spec files of the screens and APIs the step changed, from the repo's spec-to-step map, plus the specs the settings always add) as often as it needs, and **the whole-suite run once** when the coding | *Browser tests* |
| 64 | `.claude/agents/code-reviewer.md:61` | one of your own findings needs, at Normal (a `--project` you name runs every matching test on it, e.g. `--project=desktop-chromium e2e/x.spec.js -g "S0NN"`). The Full level runs only in the release (`tooling/release-tests.bat`) and when KLA asks. A new test tagged `@device` without the reason of the rule (a layout check by purpose, or a | one of your own findings needs, at the whole-suite level (a device project you name runs every matching test on it; the example: settings, *Browser tests*). The release level runs only in the release (the repo's release tests) and when the user asks. A new test with the repo's layout tag without the reason of the rule (a layout check by purpose, or a | *Browser   tests* |
| 65 | `.claude/agents/code-reviewer.md:76` | and the brief's *On a real device* checks are rows in `docs/steps/device-checks.md`. | and the brief's *On a real device* checks are rows in the repo's device-check list (settings: *Device checks*). | *Device checks* |
| 66 | `.claude/agents/code-reviewer.md:124` | - empty, no-permission and no-Team-record states rendered, not blank or a 403. | - empty, no-permission and the repo's missing-record states (settings: *Use on the floor*) rendered, not blank or a 403. | *Use on the floor* |
| 67 | `.claude/agents/code-reviewer.md:145` | - tests: `tooling/run-tests.bat`; check that the coder ran the **targeted** e2e specs of what the fix round changed (re-run only what a finding of | - tests: the repo's command for all suites (settings: *Unit tests*); check that the coder ran the **targeted** browser specs of what the fix round changed (re-run only what a finding of | *Unit tests* |
| 68 | `.claude/agents/brief-reviewer.md:3` | description: Reviews a Yantra step brief (docs/steps/S00N-*/1-brief.md) or one of its amendments, and writes the next 2-brief-review-rN.md; in staleness mode, re-checks an approved brief against code changed since its baseline (2-brief-review-sN.md). Used by the /step orchestrator; read-only apart from that one file. | description: Reviews a step brief (docs/steps/S00N-*/1-brief.md) or one of its amendments, and writes the next 2-brief-review-rN.md; in staleness mode, re-checks an approved brief against code changed since its baseline (2-brief-review-sN.md). Used by the /step orchestrator; read-only apart from that one file. | — (row i: dropped on purpose) |
| 69 | `.claude/agents/brief-reviewer.md:8` | You are the **brief reviewer** in Yantra's step workflow. The conventions are in | You are the **brief reviewer** in the step workflow. The conventions are in | — (row i: dropped on purpose) |
| 70 | `.claude/agents/brief-reviewer.md:49` | - `docs/Plan.MD` - `docs/Maintenance-Philosophy.md` - `docs/Plant-Facts.md` | - the repo's product plan and domain docs (settings: *Plan and domain docs*) | *Plan and domain docs* |
| 71 | `.claude/agents/brief-reviewer.md:65` | - contradictions with Plan.MD decisions; | - contradictions with the plan doc's decisions; | *Plan and domain docs* ("the plan doc") |
| 72 | `.claude/agents/brief-reviewer.md:83` | - **Standards.** Check that the brief names the relevant maintenance and security standards (ISO 14224, EN 13306, ISO 55000/55001, SMRP, TPM, ISO 27001) and cites them correctly. The project owner is learning maintenance practice, so explain briefly what the standard says. | - **Standards**, where the repo has a standards rule (settings: *Standards*). Check that the brief names the relevant standards the settings list and cites them correctly, and explain briefly what the standard says, as the settings ask. | *Standards* |
| 73 | `.claude/agents/brief-reviewer.md:90` | or changes, check it against how the plant works (`docs/Plant-Facts.md`, Plan.MD § 3 and § 6): | or changes, check it against how its users work (the docs the settings name: *Use on the floor*): | *Plan and domain docs* ("the plan doc") |
| 74 | `.claude/agents/brief-reviewer.md:109` | - empty and edge states: no records, no Team record, no permission (the control hidden, not a 403); | - empty and edge states: no records, the repo's missing-record states (settings: *Use on the floor*), no permission (the control hidden, not a 403); | *Use on the floor* |
| 75 | `.claude/agents/brief-reviewer.md:112` | - wording a low-literacy or Tamil-speaking user would follow, where they use the screen. | - wording the screen's users would follow, where they use the screen (settings: *Use on the floor*); - and the repo's own points (settings: *Use on the floor*). | *Use on the floor* |
| 76 | `.claude/agents/brief-reviewer.md:141` | Since S024 a brief splits its checks into **Automated** (an e2e browser test | Since S024 a brief splits its checks into **Automated** (a browser test | *Browser tests* ("browser" for "e2e") |
| 77 | `.claude/agents/brief-reviewer.md:146` | - a device check without its account, network and where (dev server on KLA's laptop, production on the TEST machine, or either) is `minor`. | - a device check without its account, network and where (the machines the settings name: *Device checks*) is `minor`. | *Device checks* |
| 78 | `.claude/agents/advisor.md:3` | description: Answers one technical question for a Yantra step (how a library, browser, operating system or device really behaves; which option works) by research and small read-only experiments, and writes docs/steps/S0NN-*/0-advice-<topic>.md. Used by the /step orchestrator for the orchestrator, a coder or a reviewer; never edits code, briefs or reviews. | description: Answers one technical question for a step (how a library, browser, operating system or device really behaves; which option works) by research and small read-only experiments, and writes docs/steps/S0NN-*/0-advice-<topic>.md. Used by the /step orchestrator for the orchestrator, a coder or a reviewer; never edits code, briefs or reviews. | — (row i: dropped on purpose) |
| 79 | `.claude/agents/advisor.md:8` | You are the **advisor** in Yantra's step workflow. The conventions are in | You are the **advisor** in the step workflow. The conventions are in | — (row i: dropped on purpose) |
| 80 | `.claude/agents/roadmapper.md:3` | description: Turns one big Yantra feature into a roadmap of steps — goals, sizes, order, dependencies, the standards it rests on and the decisions the user must make — and writes docs/roadmap/R0N-<feature>.md; re-plans an existing roadmap when asked. Used by the /step orchestrator; numbers its items R0N.n and never allocates step numbers (S0NN). | description: Turns one big feature into a roadmap of steps — goals, sizes, order, dependencies, the standards it rests on and the decisions the user must make — and writes docs/roadmap/R0N-<feature>.md; re-plans an existing roadmap when asked. Used by the /step orchestrator; numbers its items R0N.n and never allocates step numbers (S0NN). | — (row i: dropped on purpose) |
| 81 | `.claude/agents/roadmapper.md:8` | You are the **roadmapper** in Yantra's step workflow. The user (KLA) is the product owner: he | You are the **roadmapper** in the step workflow. The user is the product owner: the user | — (row i: dropped on purpose) |
| 82 | `.claude/agents/roadmapper.md:35` | 1. **Know what exists.** Read `docs/Plan.MD` (the module's section and its open questions), `docs/Maintenance-Philosophy.md` and `docs/Plant-Facts.md` (the rules and the plants), the steps already done that touch the feature (`docs/steps/README.md` index, their briefs), and the code it would build on (grep the backend modules, `docs/schema.md`). Name what is already there | 1. **Know what exists.** Read the product plan (the module's section and its open questions) and the domain docs (settings: *Plan and domain docs*), the steps already done that touch the feature (`docs/steps/INDEX.md`, their briefs), and the code it would build on (grep the backend modules, the schema doc). Name what is already there | *Plan and domain docs* |
| 83 | `.claude/agents/roadmapper.md:40` | 2. **Name the standards** the feature rests on (TPM, ISO 14224, EN 13306, ISO 55000, SMRP KPIs, and ISO 9001 clauses where they apply), each with one plain sentence of what it says and how the roadmap follows it. A clause number you have not checked is marked "to verify". The user is learning maintenance practice as the project goes. | 2. **Name the standards** the feature rests on, where the repo has a standards rule (the list: settings, *Standards*), each with one plain sentence of what it says and how the roadmap follows it. A clause number you have not checked is marked "to verify". | *Standards* |
| 84 | `.claude/agents/roadmapper.md:53` | the recommended one marked, and which items wait for it. A decision Plan.MD already settled is | the recommended one marked, and which items wait for it. A decision the plan doc already settled is | *Plan and domain docs* ("the plan doc") |
| 85 | `.claude/agents/roadmapper.md:60` | KLA approves a roadmap from a slide deck with screenshots of the feature's forms and reports | The user approves a roadmap from a slide deck with screenshots of the feature's forms and reports | — (row 1 / row j: "the user") |
| 86 | `.claude/agents/roadmapper.md:71` | - looks like Yantra: it links `../../../frontend/node_modules/bootstrap/dist/css/bootstrap.min.css` and `../../../frontend/src/assets/main.css`, uses the app's existing patterns (read the views in `frontend/src/views/` that are closest: cards, the top bar, the bottom nav on a phone, form fields, badges), and the app's labels and messages in CLAUDE-COMMON scope B; - shows plausible sample data from `docs/Plant-Facts.md` (machines, meters, units), never a real | - looks like the app: it links the repo's style sheets, uses the app's existing patterns (read the closest views; both: settings, *Roadmap mock-ups*), and the app's labels and messages in CLAUDE-COMMON scope B; - shows plausible sample data (settings: *Roadmap mock-ups*), never a real | *Roadmap mock-ups* |
| 87 | `.claude/agents/roadmapper.md:94` | Status: Draft \| Gate R \| Approved DD-MM-YYYY by KLA \| Done \| Dropped | Status: Draft \| Gate R \| Approved DD-MM-YYYY by <user> \| Done \| Dropped | — (row 1 / row j: "the user") |
| 88 | `.claude/agents/roadmapper.md:97` | Then: `## The feature` (what and why, from Plan.MD and the user), `## What exists`, `## Standards`, | Then: `## The feature` (what and why, from the plan doc and the user), `## What exists`, `## Standards`, | *Plan and domain docs* ("the plan doc") |
| 89 | `.claude/agents/roadmapper.md:106` | - no step number, no edit of `docs/steps/` or `docs/Plan.MD` (the orchestrator records approved | - no step number, no edit of `docs/steps/` or the plan doc (the orchestrator records approved | *Plan and domain docs* ("the plan doc") |
| 90 | `docs/steps/README.md:3` | Each piece of work on Yantra is a **step**. A step is planned, reviewed, | Each piece of work on the repo is a **step**. A step is planned, reviewed, | — (row i: dropped on purpose) |
| 91 | `docs/steps/README.md:116` | - it fixes behaviour that a brief, Plan.MD or the docs already describe, and | - it fixes behaviour that a brief, the plan doc or the docs already describe, and | *Plan and domain docs* ("the plan doc") |
| 92 | `docs/steps/README.md:139` | Each becomes a browser test (Playwright, `frontend/e2e/`) that the coder | Each becomes a browser test (settings: *Browser tests*) that the coder | *Browser tests* |
| 93 | `docs/steps/README.md:142` | - **On a real device** — the few a browser engine cannot judge: a real camera or QR scan, paper from a printer and a ruler, the iPhone keyboard over a dialog, a real login through Keycloak, how a gloved thumb copes. Done by the user **or the named person, today IT Admin**. | - **On a real device** — the few a browser engine cannot judge (the kinds: settings, *Device checks*). Done by the user **or the named person** (settings: *Device checks*). | *Device checks* |
| 94 | `docs/steps/README.md:149` | - **The coder** writes an e2e test for each automated check and runs `tooling/run-e2e-tests.bat`. Only a passing run may mark a check in the impl | - **The coder** writes a browser test for each automated check and runs the repo's browser tests. Only a passing run may mark a check in the impl | *Browser tests* ("browser" for "e2e") |
| 95 | `docs/steps/README.md:154` | rows to [`device-checks.md`](device-checks.md). - **The levels** (S047). `tooling/run-e2e-tests.bat` runs at one of three levels. **Basic** (`--level=basic`): the `@smoke` tests (four journeys and `screens.spec.js`) on the Android phone, about 2 minutes. **Normal** (no flag): every test on the Android phone, and the `@device` tests (layout checks, tests that differ by device) on desktop. **Full** (`--level=full`): every test on the Android phone, and the `@device` tests on the iPhone and desktop. - **The coder** runs the e2e tests whenever the frontend or an API the | rows to the repo's device-check list (settings: *Device checks*). - **The levels** (S047). The repo's browser tests run at its levels (settings: *Browser tests*): a quick whole-app run, the whole-suite run (every test on the logic device, and the layout-tagged tests, which check layout or differ by device, on the other devices the settings name), and the release level. - **The coder** runs the browser tests whenever the frontend or an API the | *Browser tests*, *Device checks* |
| 96 | `docs/steps/README.md:163` | (Normal with the spec files of the screens the step changed, plus `screens.spec.js`) as often as it needs, and may run Basic for a quick whole-app check. It runs the whole suite at Normal once, when the coding is | (the spec files of the screens the step changed, plus the ones the settings always add) as often as it needs, and may make the quick whole-app run. It makes the whole-suite run once, when the coding is | *Browser tests* (the levels by role: targeted, quick whole-app, whole-suite) |
| 97 | `docs/steps/README.md:170` | - **The Full level** runs only in the release (`tooling/release-tests.bat` runs it after the unit suites, on the same worktree of HEAD) and when KLA asks. - **`device-checks.md`** is the master list of open real-device checks, one row | - **The release level** runs only in the release (the repo's release tests run it after the unit suites, on the same worktree of HEAD) and when the user asks (settings: *Browser tests*). - **The device-check list** is the master list of open real-device checks, one row | *Browser tests* |
| 98 | `docs/steps/README.md:175` | dev server on KLA's laptop, production on the TEST machine, or either) and | machines the settings name: *Device checks*) and | *Device checks* |
| 99 | `docs/steps/README.md:189` | `Done (committed abc123; checks: 6 auto, 2 done by IT Admin, 1 skipped — iPhone)`. | `Done (committed abc123; checks: 6 auto, 2 done by <name>, 1 skipped — <reason>)` (the repo's own example: settings, *Device checks*). | *Device checks* |
| 100 | `docs/steps/README.md:223` | passing e2e run), ticked for the user or the named person (today IT Admin), | passing browser run), ticked for the user or the named person (settings: *Device checks*), | *Device checks* |
| 101 | `docs/steps/README.md:320` | `## Index` and `## Queued` (lines 320–376) | moved word for word | `docs/steps/INDEX.md` |
| 102 | `docs/steps/README.md:383` | `## Index` and `## Queued` (lines 383–399) | moved word for word | `docs/steps/INDEX.md` |
| 103 | `docs/roadmap/README.md:3` | A **roadmap** turns one big feature (a module of `docs/Plan.MD`, e.g. preventive maintenance) into an ordered list of items, each the seed of one step. The **roadmapper** (`.claude/agents/roadmapper.md`, Opus) writes it; KLA, the product owner, approves it at **gate R**; each item becomes a step only when KLA takes it up (25-10-2026, by KLA). | A **roadmap** turns one big feature (a module of the repo's product plan, e.g. preventive maintenance) into an ordered list of items, each the seed of one step. The **roadmapper** (`.claude/agents/roadmapper.md`, Opus) writes it; the user, the product owner, approves it at **gate R**; each item becomes a step only when the user takes it up (25-10-2026, by KLA). The repo's own values are in the `## Step workflow` section of its `.claude/CLAUDE.md` ("the settings"); the roadmaps are listed in `INDEX.md`, beside this file. | *the section itself* |
| 104 | `docs/roadmap/README.md:10` | Each roadmap comes with a slide deck, so KLA sees the feature before deciding on it: the feature, | Each roadmap comes with a slide deck, so the user sees the feature before deciding on it: the feature, | — (row 1 / row j: "the user") |
| 105 | `docs/roadmap/README.md:13` | in Yantra's look, sample data, static) and the slide outline (`## Slides`); the orchestrator renders | in the app's look (settings: *Roadmap mock-ups*), sample data, static) and the slide outline (`## Slides`); the orchestrator renders | *Roadmap mock-ups* |
| 106 | `docs/roadmap/README.md:22` | - **A roadmap item has no step number.** When KLA takes one up (`/step plan R0N.n`), the | - **A roadmap item has no step number.** When the user takes one up (`/step plan R0N.n`), the | — (row 1 / row j: "the user") |
| 107 | `docs/roadmap/README.md:28` | - **Gate R**: KLA approves the roadmap — its items, their order and his answers to its decisions. The orchestrator records the answers in the roadmap and the lasting decisions in `Plan.MD`. | - **Gate R**: the user approves the roadmap — its items, their order and the answers to its decisions. The orchestrator records the answers in the roadmap and the lasting decisions in the plan doc (settings: *Plan and domain docs*). | *Plan and domain docs* |

107 hunks

### 6.6 The tools, final run

After this report was written, the four tools ran again; each output was diffed with the "before" run.

- `step-check.bat`: before `S056: README row says "Approved, coding", the brief says "Implementing …" (1)`, `(shared step docs changed: docs/steps/README.md)`, `1 problem(s) in 55 steps`; after `(shared step docs changed: docs/steps/INDEX.md)`, `No problems found in 55 steps.` (S056's row and brief are now both `In code review`).
- `step-ls.bat all`: the same 55 steps and queued items. Changed: `shared step docs changed: docs/steps/README.md` → `docs/steps/INDEX.md`; S056's status, `impl report: yes` and its working-tree files (the files this report names); `working tree: M docs/steps/README.md` under the three uncommitted steps whose impl reports name the README (no longer a shared doc). Unclaimed working-tree changes: none, as before.
- `step-stats.bat`: the build time and the live numbers of this session (S056's minutes and tokens, the coder's totals, one more run, a roadmapper row from a run that finished meanwhile). No parsing difference.
- `step-feedback.bat`: the same items, plus this report's five.
- `tooling/run-tooling-tests.bat` (`YANTRA_TEST_RUN=s056c1`), last run after every edit: `== tooling: PASSED in 10 s: 263 passed`.

## Docs updated

- `.claude/CLAUDE.md`: the new `## Step workflow` section (this step's main change).
- `docs/steps/README.md`, `docs/roadmap/README.md`: the conventions, made generic (the step's
  own files).
- Plan.MD, the schema docs, the domain docs, `device-checks.md`, `example_secrets_app.py`,
  `Keycloak.md`: none, because the step changes no app module, migration, rule, device check,
  secret or role.

## Shared docs

None: not in a worktree.

## Manual checks

None (the brief has none: no screen changes).

## Feedback

- hindrance: a Bash heredoc holding a Python script with quotes and `…` failed ("unexpected EOF while looking for matching `''"), so the long scripts went through the Write tool (`claude_md.py`, 1 retry, about 2 min).
- waste: a stray `python -` line in a chained command waited on stdin until the 2-minute timeout, and the task had to be stopped (`bxvtce1z7`).
- hindrance: `grep -n -i -F -f words.txt` over the eight files core-dumped and left `grep.exe.stackdump` in the repo root; the word list went through a Python script instead (`wordgrep.py`).
- hindrance: the Write tool refused the report's draft in the scratchpad ("Subagents should return findings as text"), so the report went in as a placeholder plus one Edit (1 call lost; the same happened in S049).
- rule: § 1.1 row b moves item 12's "(S021 CR1-01)" to the settings, while BR1-07 keeps every evidence tag; I followed row b (D6), but the two rules disagree.

## Fix rounds

### Round 1 (code review r1)

- **CR1-01 (minor)** — Deferred: for the orchestrator at commit time. KLA's decision: R01 is committed
  separately after S056. I did not edit or move `docs/roadmap/R01-auth-hardening.md`; the R01 row stays in
  `docs/roadmap/INDEX.md`. I changed only that row's line ending to CRLF (the file is now CRLF on all
  10 lines, no lone CR).
- **CR1-02 (nit)** — Fixed: named in D2 above (the "never" list now also names `useFormModal.js` and the
  auth store; the settings entry holds the list).
- **CR1-03 (nit)** — Fixed, by KLA's decision: "(S021 CR1-01)" is back inline in self-check item 12 of
  `.claude/skills/step/SKILL.md`, replacing "(provenance: settings, *Self-check, repo items*)". The
  sentence "(12) The parser rule comes from S021 CR1-01." is removed from the settings entry in
  `.claude/CLAUDE.md` § Step workflow. This supersedes D6.
- **CR1-04 (nit)** — Fixed: `roadmapper.md` "a part of the plant" is now "a part of the business".
- **CR1-05 (nit)** — Fixed: one name, "the repo's product plan", in SKILL.md (all "the plan doc" places
  and the item 8 title), `brief-reviewer.md:65`, `roadmapper.md` (37, 54, 97, 106), `docs/roadmap/README.md:32`
  and `docs/steps/README.md` (116 and the table row). SKILL.md:566 reads "(product plan, schema doc, …)".
- **CR1-06 (nit)** — Fixed: SKILL.md "(the pure core of PM triggers, KPIs)" is now "(e.g. the pure core of a
  schedule or a KPI)".
- **CR1-07 (nit)** — Fixed: "Fix-lane criteria" in the `.claude/CLAUDE.md` entry and in the README table row
  ("for the fix-lane criteria").

No test was added or changed (text only), so no red run applies.

**Line endings.** My first `sed -i` pass (Git Bash) rewrote four CRLF files as LF; I found it by counting
bytes in Python and restored CRLF in `SKILL.md`, `roadmapper.md`, `CLAUDE.md` and `docs/roadmap/README.md`.
Final byte check: those four and `docs/roadmap/INDEX.md` are all CRLF with no lone CR; `docs/steps/README.md`
and `brief-reviewer.md` are LF as before.

**Docs updated.** `.claude/CLAUDE.md` (settings entry) and `docs/steps/README.md`; no other doc is due.

#### Feedback

- hindrance: `sed -i` in Git Bash silently turned CRLF files into LF, and `grep -c $'$'` could not show it (it reported all lines as CRLF); only a byte count in Python did (4 files restored, ~5 min).
- idea: a `tooling` helper that prints CRLF/LF/lone-CR counts per file would replace the ad-hoc Python check.
