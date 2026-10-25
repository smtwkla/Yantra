```
Step: S056 — The step workflow names no repo: Yantra's specifics move to its settings
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S056 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The refactor holds. Every Yantra rule reads the
same through the new generic text and its `## Step workflow` entry. I found one `minor` and six
nits. The minor is for the orchestrator at gate B: `docs/roadmap/INDEX.md` holds a row from the
parallel R01 roadmap run. The nits are wording and the D1/D6 calls KLA makes at gate B.

**Test result.** `YANTRA_TEST_RUN=s056cr1 tooling/run-tests.bat`: **ALL SUITES PASSED**. Backend
3075 passed, frontend 179, deps 42, tooling 263. No frontend source changed, so no build check is
needed. No browser run is needed: the step changes no screen and no API. The brief has no
automated or device checks.

## The § 5 checks, re-run

I re-ran each check myself. The "before" text was `git show 82997ee:<path>` and the coder's
`orig/` copies, because the S056 index row and the line endings were uncommitted at 82997ee. My
script is `C:\Users\KLA\AppData\Local\Temp\claude\C--Users-KLA-PycharmProjects-Yantra\4cb08d41-5654-498e-a3ec-a8406a3f2557\scratchpad\check.py`.

| Check | My result | Agrees with the impl report |
|---|---|---|
| Word list (§ 5 pattern, case-insensitive, eight prose files) | 250 lines before, 28 after. The 28 are 22 `KLA` provenance tags, 3 "blank" (the English word), 1 "normalised", and 2 `S001-basic-masters` / "Basic masters" (D1) | Yes. The report says 251 before; mine is 250 against HEAD, because the uncommitted S056 index row is not in HEAD |
| Token conservation (set difference per file) | 0 backticked tokens without a home in `CLAUDE.md` or an `INDEX.md` | Yes |
| Token conservation (the brief's `--word-diff=porcelain`) | The word-diff joins wrapped lines and breaks backtick pairs, so most of its "tokens" are noise. The real multi-word tokens it flags are in the settings with single spaces (e.g. the `run-backend-tests.bat` example and the `--project=desktop-chromium` example) | Supports D12. But D12's "stricter" is not right: set difference misses a token removed at one place and kept at another. The round trip below covers that case |
| Outline (`^#` lines) | `docs/steps/README.md`: `## Index` and `## Queued` gone, `## The repo's settings and index` added. `docs/roadmap/README.md`: `## Index` gone. Nothing else lost or reordered | Yes |
| `step-check.bat` | The same as the coder's final run, plus `?? docs/roadmap/R01-auth-hardening.md: no step claims it (10)`. That file appeared at 20:47, after the coder's run (CR1-01) | Yes |
| `step-ls.bat all` | The same as the coder's final run, plus R01 among the unclaimed changes. Against "before": "README" became "INDEX.md" in the shared-docs line, and `working tree: M docs/steps/README.md` shows under the three steps whose impl reports name the README | Yes |
| `step-stats.bat` | Only the build time and the live counts of this session differ | Yes |
| `step-feedback.bat` | No difference from the coder's final run | Yes |
| `INDEX.md` moved word for word | `docs/steps/INDEX.md` from `## Index` to the end equals the README's old part line for line, except S056's own row (D9: new summary, status `In code review`). `docs/roadmap/INDEX.md`: the header and separator moved; the R01 row is new (CR1-01) | Yes, apart from R01 |
| `parse_index` on the new `INDEX.md` | 55 index rows and 1 queued row with an ID (S048). That is 56 lines starting `| S0`, so every row parses. The last row is `S056 … In code review` | — |
| `grep -rni readme tooling/` (.py, .bat, without `deps/`) | No hit. No tool reads the README any longer; no caller of the renamed `readme_status` or `check_stage_matches_readme` is left | Yes (§ 6 Q2) |
| Line endings | Each prose file, `CLAUDE.md` and the three tooling files keep their before style. CRLF: SKILL.md, coder.md, code-reviewer.md, roadmapper.md, roadmap README, CLAUDE.md, step_facts.py, step_check.py. LF: advisor.md, brief-reviewer.md, steps README, test_step_facts.py. `docs/steps/INDEX.md` is LF, like its source. `docs/roadmap/INDEX.md` is CRLF except the R01 row (LF; CR1-01) | Yes |
| Lone CRs | None in any of the 15 files | Yes |
| Backslash paths | The backslash lines are unchanged: SKILL.md 2, roadmap README 1, CLAUDE.md 4 (`docs\roadmap\R0N-mockups`, `tooling\release-tests.bat`, the SQL's `\_`) | Yes |

## The round trip (§ 5)

Each row of § 1.1's two tables. "Yantra reading" is the new generic sentence read with its
settings entry. Every reading says what the old line said, apart from the notes.

| Row | New generic sentence → entry | Yantra reading | Same as before? |
|---|---|---|---|
| KLA | "the user" | KLA approves, answers and commits. Provenance tags keep "by KLA" | Yes |
| IT Admin | "the named person" → *Device checks* | IT Admin does the device checks the user hands over | Yes |
| Unit-test commands | "the repo's command for all suites", "per-suite commands", "build check" → *Unit tests* | `tooling/run-tests.bat` once at the end and in each review round; `run-backend-tests.bat <files>` / `run-frontend-tests.bat <file>` while coding; `npx vite build` in `frontend/` when the frontend changed | Yes. *Unit tests* also lists `run-tooling-tests.bat`, a per-suite command the brief's row names |
| `YANTRA_TEST_RUN` | "the repo's test run name variable", "the reserved names" → *Unit tests* | Set `YANTRA_TEST_RUN` to your own name; never `dev` or `release` | Yes |
| Browser tests, levels, tags, projects | "quick whole-app run / whole-suite run / release level", "targeted run", "layout tag", "logic device" → *Browser tests* | Targeted = Normal with the changed specs plus `e2e/screens.spec.js`. Quick = Basic. Whole suite = Normal, once at the end of coding. Release = Full, only in `tooling/release-tests.bat` and when KLA asks. A new test runs alone first: `E2E_LANES=1`, `--project=phone-chromium -g "S0NN"`. The `@device` tag is only for a layout purpose or a device difference; a logic test with `expectDialogFits` stays untagged | Yes. The reviewer's "at the whole-suite level" means Normal, as before |
| Plan, domain docs | "the plan doc", "the domain docs" → *Plan and domain docs* | `docs/Plan.MD`; `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md` | Yes (term: CR1-05) |
| Standards rule | "the repo's rule on standards, if it has one" → *Standards* | § Standards and best practice: name TPM, ISO 14224, EN 13306, ISO 55000/55001, SMRP, ISO 27001, ISO 9001 clauses; explain each in plain words; gate reports name the standards touched | Yes. Each agent now reads the union of the lists. Before, the roadmapper's list lacked ISO 27001 and ISO 55001, and the brief reviewer's lacked ISO 9001. "Relevant" still filters, so no rule changed |
| Self-check items (locks, keys, tests, guards) | items 2, 3, 5, 10 → *Self-check, repo items* | (2) compare with the LOCK ORDER notes of `tickets.py` and `masters.py`; REPEATABLE READ. (3) the key's site (`SITE_SCOPED`); senior reads scoped to the sites where the key is held. (5) always `test_role_matrix`, `conftest.py` `_TABLES`, `db_down`, `test_migration_*`. (10) `_PRECONDITIONS` against production's rows | Yes, item by item |
| Shared frontend files | "the repo's shared frontend files" → *Shared code* | A change to `FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store or `e2e/support/` allows a second whole-suite run | Yes |
| Device-check list, machines | "the repo's device-check list", "the machines the settings name" → *Device checks* | Rows go to `docs/steps/device-checks.md`; where = the dev server on KLA's laptop, production on the TEST machine, or either | Yes |
| Mock-up styles | "the repo's style sheets", "the closest views" → *Roadmap mock-ups* | Link the two `../../../frontend/…` style sheets; copy from `frontend/src/views/`; sample data from `Plant-Facts.md` | Yes |
| Skill front matter | "Orchestrate the step workflow …" | — | Yes (row i) |
| a. UX checklist | Stays in the agents; plus "the repo's own points" → *Use on the floor* | Judge against `Plant-Facts.md` and Plan.MD § 3 and § 6; the missing-record state is no Team record; wording for a low-literacy or Tamil-speaking user | Yes (Q3) |
| b. Self-check items 1, 11, 12, 13 | → *Self-check, repo items* | (1) QR, Pillow, Bootstrap, urllib checks; grep the devops repo, compose and cron. (11) the database down (§ DB may not exist) and the worker's tasks. (12) S021 CR1-01. (13) what `blank` returns and what `open(seed)` does | Yes. Item 16 has no content of its own (D8) |
| c. Fix-lane criteria | "the repo's permission tables and gates", "the security-sensitive code the repo names" → *Self-check, repo items* | No `SITE_SCOPED`, no network gate, no push or email addresses on the fix lane | Yes. The entry also names "Opus criteria", which point nowhere (CR1-07) |
| d. Parallel steps | "the repo's migrations module and the schema docs", "shared frontend code", "shared test fixtures" → *Shared code* | Never in parallel: two migrations (`local_db.py`, schema docs); the same screen; the nav, `FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store, `e2e/support/`; the same `conftest.py` entries | Yes in meaning. The list now names `useFormModal.js` and the auth store too (CR1-02) |
| e. Release flow | "the release level … the repo's release tests … when the user asks" → *Browser tests* | Full runs only in `tooling/release-tests.bat`, after the unit suites, and when KLA asks | Yes. The entry points at § Yantra Specifics *Release*, not § Pre-flight as row e says. *Release* is the section that describes the release tests, so this pointer is the better one |
| f. Spec-to-step map | "the repo's spec-to-step map" → *Browser tests* | The map in § SMTW-Review | Yes |
| g. Sample commands | moved to *Unit tests*, *Browser tests*, *Roadmap mock-ups* (D2) | The same examples, now in the settings | Yes. Nothing was dropped |
| h. Device-only kinds, device projects | "the checks a browser engine cannot judge" → *Device checks*; "device projects" → *Browser tests* | Camera or QR, paper and ruler, the iPhone keyboard, a real Keycloak login, a gloved thumb; `phone-chromium` / `desktop-chromium` / `phone-webkit` | Yes |
| i. Agents' first lines | "the step workflow", "the user is the product owner" | — | Yes |
| j. Templates | "by <user>" | — | Yes |
| k. Stack words | unchanged | — | Yes |
| l. "learning maintenance" | dropped from the generic text → *Standards* | "The project owner (KLA) is learning maintenance practice … each standard explained briefly" | Yes |

**The rules I read hardest.** None of them is weakened:
- **Self-check items 1–15** read the same; I compared each one above.
- **The fix-lane criteria** read the same: the generic text names the class, and the entry names
  Yantra's tables and gates.
- **The browser-run rules** read the same: one whole-suite run at the end of coding, targeted runs
  in fix rounds, the reviewer never runs the whole suite, Full only in the release.
- **The docs pass** text is not changed; it already pointed at `CLAUDE.md` § Docs to keep current.
- **Gate B's report** keeps every bullet. It lost only the command name in "the browser-test
  result", which changes nothing.
- **The async verify review** has no change.
- **The parallel-steps "never" list**: see CR1-02.

## Findings

### CR1-01 (minor) — `docs/roadmap/INDEX.md:10` holds the R01 row of a parallel roadmap run

- **Problem.** The R01 row (`| [R01](R01-auth-hardening.md) | Auth hardening … | Draft — at gate R |`)
  is not in the old roadmap README, so it was not moved. The orchestrator of the R01 run added it
  at 20:47, after the coder's last tool run. It ends with LF only, in a file that is otherwise
  CRLF. The impl report does not mention it, and `step-check.bat` now reports
  `?? docs/roadmap/R01-auth-hardening.md: no step claims it (10)`.
- **Failure scenario.** At gate B, S056's snapshot or commit takes `docs/roadmap/INDEX.md`, a new
  file of S056, with the R01 row in it. If `R01-auth-hardening.md` is not committed with it, the
  committed index links to a file that is not in the tree. `/step check` then keeps flagging R01
  as unclaimed.
- **Fix (orchestrator, at gate B; not the coder).** Choose one:
  1. Commit `R01-auth-hardening.md` with S056, or before it.
  2. Keep the R01 row out of S056's snapshot and add it when R01 is recorded.

  In both cases, make the row's line ending CRLF like the rest of the file.

## Nits

- **CR1-02** (nit) `.claude/skills/step/SKILL.md:548` with *Shared code*: the parallel "never" list
  now also names `useFormModal.js` and the auth store. I count this as the same rule, because the
  old parenthesis listed examples of "shared frontend code". Add one line to D2 or D11 so KLA sees
  it at gate B.
- **CR1-03** (nit) `.claude/skills/step/SKILL.md:234`: the pointer "(provenance: settings, *Self-check,
  repo items*)" sends an agent to the settings for no rule (D6). I recommend restoring "(S021
  CR1-01)" in place, as BR1-07 keeps every other evidence tag (e.g. "S021, 57 files" at `:159`).
  Then drop "(12)" from the entry. KLA decides at gate B. Row b and BR1-07 really do disagree, and
  the coder followed row b correctly.
- **CR1-04** (nit) `.claude/agents/roadmapper.md:56`: "a part of the plant not yet described" is a
  domain word that D1 does not list. Write "a part of the business not yet described", or add it to
  D1's list.
- **CR1-05** (nit) `.claude/skills/step/SKILL.md:114, 290, 438, 453, 689`; `brief-reviewer.md:51, 65`;
  `roadmapper.md:37, 54, 97, 106`; roadmap `README.md:3`: one thing has three names, "the plan
  doc", "the product plan" and "the repo's product plan". Use "the product plan" everywhere, as
  the README's entry table does.
- **CR1-06** (nit) `.claude/skills/step/SKILL.md:317`: "(the pure core of PM triggers, KPIs)" is the
  one D1 example that a non-maintenance repo would misread. "(e.g. the pure core of a schedule or
  a KPI)" keeps the picture. My other D1 calls are below.
- **CR1-07** (nit) `.claude/CLAUDE.md:52` (*Self-check, repo items*) and `docs/steps/README.md:336`:
  "Fix lane and Opus criteria". The Opus criteria (`SKILL.md:312-318`) carry no settings pointer
  and never named `SITE_SCOPED` or push addresses. Write "Fix-lane criteria" in both places.

## D1–D12, for KLA at gate B

- **D1. Examples off the word list.** My recommendation for each:

  | Example | Recommendation | Why |
  |---|---|---|
  | `Step: S001 — Basic masters`, `docs/steps/S001-basic-masters/`, the `S001:` commit example (README) | Stay | Format examples. They show the shape, and the same text works in any repo |
  | "UI on the masters pattern" (SKILL.md:76) | Stay | "Masters" screens are a shared SMTW pattern |
  | "the badge, the timeline line, the times card" (README) | Stay | It shows "what the user would see"; the reader needs no Yantra knowledge |
  | `ApiError`, `btn-sm` (code reviewer) | Stay | SMTW stack names (base and Bootstrap), like row k |
  | The roadmapper's user story ("PM jobs"), `01-todays-jobs.html`, "Technician A" | Stay | Format examples for a story and a file name. Moving them to the settings costs an entry for no rule |
  | "(the pure core of PM triggers, KPIs)" (SKILL.md:317) | Make generic in place | CR1-06 |
  | "e.g. preventive maintenance" (roadmap README:3–4) | Either | Harmless. Dropping it costs one word |
  | "a part of the plant" (roadmapper.md:56) | Make generic in place | CR1-04; it was not listed |

  None of them belongs in the settings: an example is not a value any rule depends on.
- **D2** (row g moved instead of dropped): right. No information is lost, and the token check
  needs no "dropped" list.
- **D3** (renames to `index_status` and the rest): right. One term; I found no caller left.
- **D4** (the old bullet as prose at the section's top): right. It matches § 1.2's "first lines",
  and a bullet parser skips it.
- **D5** (`none` column): matches § 1.2; no new rule.
- **D6** (item 12's provenance): see CR1-03. I recommend keeping the tag inline.
- **D7** (item 4 unchanged): right. "site" reads as a general scope.
- **D8** (item 16): it follows row b. It has no content of its own today; that is harmless.
- **D9** (S056's own row rewritten): right. The old summary described the rejected design.
- **D10** ("e2e" to "browser"): right, and consistent across the files.
- **D11** (extra values in the settings): each one is a fact from the old files or `CLAUDE.md`;
  no rule is new.
- **D12** (token check by set difference): an acceptable method; my word-diff run shows why the
  brief's method is noisy. The claim "stricter" is wrong (see the checks table). The round trip
  covers the case it misses.

## The dry run, on paper

The imaginary step: S058 adds a "Notes" text field to the equipment-class master dialog. It needs
a migration, so it runs on the full track. I read only the new files and the settings.

1. **The orchestrator plans it.** The skill sends it to the settings section; the section exists.
   The next free ID comes from `docs/steps/INDEX.md`; the brief and its row go there too. The track
   criteria are generic: a migration means full. The facts run is `tooling/step-brief-facts.bat
   S058`, from the section's first paragraph.
2. **The checks.** Automated: a browser test that the dialog saves the note and shows it
   (*Browser tests*). On a real device: none, because nothing in *Device checks*' kinds applies.
   Standards: *Standards* points at § Standards and best practice (ISO 14224, the equipment
   taxonomy).
3. **The self-check.** Item 2: the LOCK ORDER of `masters.py`. Item 3: the class edit key and
   whether it is in `SITE_SCOPED`. Item 5: `test_role_matrix`, `_TABLES`, `db_down`,
   `test_migration_*`. Item 10: `_PRECONDITIONS` (an added NULL column needs none). Item 11: the
   database down. Item 13: `useFormModal`'s `blank` and `open(seed)`. Each item resolves.
4. **The brief reviewer** reads the plan and domain docs (*Plan and domain docs*). It judges the
   dialog against `Plant-Facts.md` and Plan.MD § 3 and § 6 (*Use on the floor*). At gate A, the
   decisions go into `docs/Plan.MD`.
5. **The coder** uses `YANTRA_TEST_RUN=s058c1`. While coding it runs `run-backend-tests.bat` on the
   masters tests. The new test runs alone with `E2E_LANES=1 … --project=phone-chromium -g "S058"`.
   The targeted run is `masters.spec.js` plus `screens.spec.js`, from the spec-to-step map. Then
   one Normal run, `tooling/run-tests.bat`, and `npx vite build`. The status goes into its row in
   `INDEX.md`. The docs pass updates the schema docs.
6. **The code reviewer** runs `tooling/run-tests.bat`, and checks the `@device` rule from
   *Browser tests* and the UX list with the missing-record state (*Use on the floor*).
7. **Gate B and Done** use the generic report, and the Done example from *Device checks*.
   `step-check.bat` compares the brief's status with `INDEX.md`.

**Result.** Every instruction could be followed from the new files and the settings alone. No step
needed the old text. One small friction: the product plan has three names (CR1-05).

## Checked and found consistent

- The brief's § 1.2 stop message for a repo without the section: it is in the README's new
  section and the skill's opening, word for word.
- The README's new section: the nine entries match the settings' nine bullets by name and form.
  The index shape matches `parse_index`: two tables, the status in the fourth cell, the queued
  rows with or without an ID.
- `INDEX.md`'s head says the index was in the README until S056 (BR1-08).
- Every steps-index reference in § 1.3's list now names `INDEX.md`. The git-index uses
  (`SKILL.md` § Snapshots, `step_snapshot.py`) are unchanged.
- References to the conventions keep `docs/steps/README.md` § …
- `CLAUDE.md`: the old *Step workflow* bullet is gone from § Yantra Specifics. It reappears once,
  at the top of § Step workflow, with the two `INDEX.md` paths added.
- The tooling diff is limited to the index path, `SHARED_DOCS`, the messages, the renames and the
  docstrings. The tests assert the new messages.
- Scope: nothing of S057 is touched (`step_stats.py`, `brief_facts.py`, the `.bat` files, sync).
- Docs pass: `## Docs updated` names `CLAUDE.md` and the two READMEs. No other doc of § Docs to
  keep current is due, because there is no migration, rule, device check, secret or role.
- Track: full, as the brief says. Writing style: the impl report follows scope A. No screen text
  changed.
- Manual checks: the brief has none, and the report says so.

## Manual browser checks for the user

None. The step changes no screen.

## Feedback

- hindrance: `cmd //c tooling\\run-tests.bat` from Git Bash lost the backslash ("'toolingstep-check.bat' is not recognized"), so I ran the tools again as `./tooling/x.bat` (2 runs lost, about 2 min).
- waste: the brief's `git diff --word-diff=porcelain` token check gives mostly noise on wrapped Markdown, because the words of a line-wrapped backtick span land on separate lines (one run, about 3 min to see why).
- idea: a reviewer would not need the coder's `orig/` copies if the coder committed nothing but recorded the before-state hash of uncommitted files, or if `step-snapshot` could snapshot the before state (the S056 row and line endings were not in 82997ee).
- rule: § 1.1 row b and BR1-07 disagree on item 12's provenance tag (D6); the next generic-ising brief should say that step IDs in evidence tags always stay.
