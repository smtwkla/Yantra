```
Step: S056 — The step workflow names no repo
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 82997ee (the working tree holds only S056's own folder and its README row; no other step is uncommitted)

**Verdict: one `major` finding is open (BR1-01: § 1.1's table misses whole categories of Yantra text, so the coder would decide alone what is Yantra's). No `blocker`.** Five `minor` findings and four nits. Facts file `scratch/brief-facts-S056.md` was given and used. Full track, round 1. The step is right to be full: it rewrites the instructions every agent follows.

The design holds: settings in `CLAUDE.md` as `## Pre-flight` does, the conventions kept in a generic `docs/steps/README.md`, the index in `docs/steps/INDEX.md`, the tools reading it there. The findings are about completeness (what counts as Yantra's), the places the index move touches, and how the "nothing is lost" check is made sharp.

## Findings

### BR1-01 — major — § 1.1's table misses categories; the coder would sort them alone

**Problem.** The table lists the Yantra values a grep for "commands, files, levels, docs, roles and names" finds. I grepped the skill, the five agent files and the two READMEs for a wider set (domain words, sample paths, CLAUDE.md section names, examples, the stack). These categories are in the files and not in the table:

| # | Category | Evidence (file:line) | Proposed generic text / where the value goes |
|---|---|---|---|
| a | **The domain UX checklist** — the whole "Use on the floor (UX)" block: the plant, the floor, gloved hands, kiosk logins, "no Team record", a supervisor at shift end, Tamil-speaking users, `docs/Plant-Facts.md`, Plan.MD § 3 and § 6 | `brief-reviewer.md:87-117`; `code-reviewer.md:110-129` ("floor screens", `btn-sm`, `ApiError`, "no-Team-record states") | A decision for the user, see below |
| b | **Repo-specific self-check items that are not names**: item 11 (the DB down and the worker), item 13's composable contract (`blank`, `open(seed)`), item 12's provenance (S021 CR1-01), item 2's REPEATABLE READ (MariaDB's isolation level), item 1's library examples (QR version, Pillow, Bootstrap, urllib) and "the devops repo, compose and cron" | `SKILL.md:177-178, 185, 221-224, 226, 228-231` | Items 11 and 13's Yantra parts move to settings *Self-check, repo items*; the generic list keeps a last item "the repo's own items (settings)". Library examples: drop, or move to the same entry |
| c | **The fix-lane and Opus criteria that name Yantra's code**: `SITE_SCOPED`, "the network gate", "push or email addresses" | `SKILL.md:111, 114-115` | "the repo's permission tables and gates (settings: *Self-check, repo items*)"; "security-sensitive code the repo's `CLAUDE.md` names" |
| d | **The migrations file and the always-conflicting files** in § Parallel steps: `local_db.py`, `conftest.py` entries | `SKILL.md:539, 543` | "the repo's migrations module and schema docs"; the file names to settings *Shared code* |
| e | **The release flow**: `tooling/release-tests.bat`, "when KLA asks" | `SKILL.md:355-357`; `coder.md:141-142`; `code-reviewer.md:63-64`; `README.md:170-172` | Row *Browser tests* says "its release level" but not the command. Name `tooling/release-tests.bat` in settings *Browser tests* (it is already in `CLAUDE.md` § Pre-flight, so a pointer) |
| f | **CLAUDE.md section names used as pointers**: the spec-to-step map in `§ SMTW-Review` | `coder.md:130`; `code-reviewer.md:57` | Settings *Browser tests*: "the spec-to-step map: `CLAUDE.md` § SMTW-Review". (`§ Docs to keep current` is already generic: the skill says what to do without it, `SKILL.md:332-333`) |
| g | **Sample paths and example commands**: `tests/test_tickets_core.py tests/test_ticket_work_api.py`, `e2e/tickets-work.spec.js`, `frontend/`, `frontend/e2e/`, `frontend/src/views/`, "Track: light — UI on the masters pattern" | `coder.md:91-93, 95, 101, 131-132`; `roadmapper.md:73`; `SKILL.md:71` | Keep the sentence, drop the Yantra example, or make the example the settings entry's ("e.g. the settings' *Unit tests* command with a test file") |
| h | **The kinds of device-only check**: "camera, paper, the iPhone keyboard, a real Keycloak login", "a real camera or QR scan, paper from a printer and a ruler", the e2e project names `phone-chromium`, `desktop-chromium`, `phone-webkit`, "the Android phone", "the iPhone" | `SKILL.md:144-145`; `README.md:139-145`; `coder.md:107-109, 117, 122-123` | Row *Device checks* covers the file, the person and the machines, not the kinds; row *Browser tests* covers the levels, not the devices. Add both to the two entries |
| i | **The agents' front matter and first line**: "Reviews a Yantra step brief", "You are the **coder** in Yantra's step workflow", "The user (KLA) is the product owner" | `coder.md:3, 7`; `code-reviewer.md:3, 8`; `brief-reviewer.md:3, 8`; `advisor.md:3, 8`; `roadmapper.md:3, 8` | The table's last row covers only the skill's front matter. Add the five agents: "a step brief", "the step workflow" |
| j | **Templates that name KLA**: the roadmap header `Approved DD-MM-YYYY by KLA`; the advisor's and roadmapper's "KLA approves" | `roadmapper.md:94, 60`; `docs/roadmap/README.md:5, 10, 28` | "by <user>", as `README.md` § Header block already writes it |
| k | **The stack**: Bootstrap `modal-dialog-scrollable`, `node_modules/`, the backend's `.venv`, `uv run --no-project python`, `node -e`, PowerShell | `code-reviewer.md:115`; `advisor.md:27, 31` | State in the brief that the SMTW stack (CLAUDE-COMMON § Defaults: Python + uv, Vue + Bootstrap, Windows) is *not* a Yantra specific and stays. Otherwise the coder has to decide |
| l | **"The user is learning maintenance practice"** as the reason for naming standards at the gates | `SKILL.md:696`; `brief-reviewer.md:85`; `roadmapper.md:43` | Row *Standards* covers the rule, not the reason. Move the reason into the settings entry or drop it from the generic text |

**Why it matters.** The brief calls this a pure refactor with the equivalence check as its guard (§ 5). The check greps for the words of § 1.1. A category the table misses is a category the grep misses, so neither the coder nor the check will see it. Category (a) is the largest block of Yantra text outside the table (about 30 lines in `brief-reviewer.md`, 20 in `code-reviewer.md`), and the brief's "3–31 Yantra lines per agent" undercounts it.

**Options.**
- (1) Add a row per category above, with the generic text and the settings entry, as the table does today. **Recommended** for b–l.
- (2) For (a), the UX checklist, a decision for the user, because it changes where a long rule lives:
  - (2a) **Recommended**: the checklist stays in `brief-reviewer.md` as the generic list for apps used on a phone by shift workers (that is every SMTW floor app), and only its Yantra lines move to a settings entry *Use on the floor*: the domain docs to judge against (`docs/Plant-Facts.md`, Plan.MD § 3 and § 6), "no Team record", the Tamil-speaking users. The generic text says "and the repo's own points (settings: *Use on the floor*)". Cheap; `CLAUDE.md` grows by three lines.
  - (2b) The whole checklist moves to `CLAUDE.md` § Step workflow. `CLAUDE.md` grows by 30 lines that every session loads, against decision 4 (pointers, not copies).
  - (2c) A new `docs/ux-checklist.md`, pointed at from the settings. One more file; right only if other repos will want a different list.

### BR1-02 — minor — § 1.3 leaves the index references to the coder; the list is short, and two "index" words are git's

**Problem.** The brief says "the coder sorts which mean the index and which the conventions". I sorted them. Of the 17 mentions of `docs/steps/README.md`, two mean the index: `roadmapper.md:37` ("`docs/steps/README.md` index") and `SKILL.md:609` ("from the index in `docs/steps/README.md`"). The others name the conventions and stay. The index is also meant, without the path, at:

- `SKILL.md:68, 94, 122, 139, 140` ("the index row", "the README index", "add the index row"); `:557` ("not the README index"); `:587` ("the shared docs changed (README, `device-checks.md`)"); `:638` (check 1's text);
- `coder.md:51, 159`; `brief-reviewer.md:25`;
- `README.md:95` ("the index row"), `README.md:226` ("its row in the index **below**" — wrong once the index is in another file);
- `step_check.py:8, 53, 137, 140` (the brief names these); `test_step_facts.py:217` asserts "has no README row" and its fixture is named `README` (`:12`);
- the roadmap index: `SKILL.md:26` ("lists the roadmaps from `docs/roadmap/README.md`"), `SKILL.md:434-435` ("Add the roadmap's index row in `docs/roadmap/README.md`"), `roadmapper.md:17` ("`docs/roadmap/README.md`'s index").

Two places say "index" and mean **git's index**; a search-and-replace must leave them alone: `SKILL.md:519` ("sets the index to its files"), `step_snapshot.py:10, 13, 93-102, 123`, `step-snapshot.bat:3`.

`CLAUDE.md` has no reference to the index: its one mention (`:11`) names the README for the conventions. § 3's row for `CLAUDE.md` ("its references to the index say `docs/steps/INDEX.md`") has nothing to change.

**Why it matters.** A rule left to the coder, and a grep-and-replace trap. Listing 20 lines in the brief costs less than a fix round.

**Options.** (1) **Recommended**: put the list above in § 1.3 (or an appendix), with the git-index exceptions. (2) Keep the delegation and add only the exceptions. Either way correct § 3's `CLAUDE.md` row.

### BR1-03 — minor — the generic README must define INDEX.md's shape, because the tools parse it

**Problem.** `step_facts.parse_index` (`:31-47`) reads the index by shape: a row `| S0NN | [title](folder/…` (`INDEX_ROW`, `:18`), the status in the fourth cell (`:46`), and a `## Queued` heading after which rows starting `| S0NN` are queued items (`QUEUED_ROW`, `:19`, `:36`). Checks 1 and 8 of `step_check.py` (`check_stage_matches_readme`, `check_folders`) and `/step ls` depend on it. Today that shape is defined by example only, in the index itself, which moves to the repo-specific `INDEX.md`. The brief gives the generic README "one line: the repo's steps are listed in `INDEX.md`".

**Why it matters.** After the lift, another repo writes its own `INDEX.md`. If its first row is `| S001 | Basic masters |` with no link, `/step ls` lists nothing and `/step check` reports every folder as "has no row". The shape is a convention, so it belongs in the conventions file.

**Options.** (1) **Recommended**: the README's new pointer section states the shape in five lines: the two tables (`## Index`, `## Queued (not yet briefed)`), the columns, the title cell as a link to `S0NN-<slug>/1-brief.md`, the status cell as the fourth column, and that the step tools read it (`tooling/steps/step_facts.py`). INDEX.md's two-line head says the same in one line. (2) Leave it to S057's lift list. Then the first other repo finds out from a silent empty listing.

For `docs/roadmap/INDEX.md` nothing parses it (the orchestrator and the roadmapper read it); a one-line shape note is enough.

### BR1-04 — minor — § 1.2: fix the entry form and the "none" case now, and say what happens to the existing *Step workflow* bullet

**Problem.** Three things § 1.2 leaves open:

1. **The entry form.** `## Pre-flight` is read by a script (`preflight.py:38-39, 63`: `SECTION = "## Pre-flight"`, bullets `- **Label**: value`) and by the skill ("from the heading to the next `## `", `pre-flight/SKILL.md:25-26`). § Out of scope says S057's `brief_facts.py` (`SEARCH_DIRS`) and `step_stats.py` will read the settings. The brief says "a list, one entry per row" and no more. If the coder writes prose entries, S057 rewrites them.
2. **`none`.** Rows say "where the repo has browser tests", "if it has one" (standards). A repo without browser tests, domain docs, a standards rule, a named person or shared frontend files needs one rule: each entry may be `none`, and the generic text says what the step does then (no browser tests: every manual check is a device check and the coder writes none; no standards rule: § 2 of a brief says "none applies"; no named person: the user does the device checks).
3. **Two places named "Step workflow".** `CLAUDE.md:11` is already a bullet **Step workflow** in § Yantra Specifics (the tools, the gates, the snapshot rule). The brief adds a `## Step workflow` section and does not say whether the bullet stays, moves into the section, or becomes a pointer. One term, two things (CLAUDE-COMMON § Writing style rule 4).

**Why it matters.** (1) and (2) are rules the coder would otherwise decide; (3) is a reader's confusion in the file every session loads.

**Options.** (1) **Recommended**: § 1.2 fixes the form as `- **<Entry>**: <value>` with the entry names of § 1.1's right column, allows `none` with the one-line consequence per entry, and moves the `:11` bullet's tool list into the section (the bullet becomes "**Step workflow**: see § Step workflow below"). (2) Prose entries now, S057 restructures: double work.

### BR1-05 — minor — § 5's equivalence check cannot catch the two main ways a rule is lost

**Problem.** The check has two parts: the coder's table of changed lines from "the grep of § Today", and the reviewer reading the new files "together with" the settings. Two faults pass both:

- **a category the grep does not know** (BR1-01): the grep pattern is built from § 1.1, so a Yantra line outside its words is never in the table, and the reviewer has no list to check it against;
- **a rule weakened with no Yantra word changed**: "always check `test_role_matrix`, `conftest.py` `_TABLES` …" becoming "check the existing tests" (the settings entry listed but never pointed at) changes nothing the grep sees, and a 1,400-line read-through finds it only by luck.

**Why it matters.** The brief names this risk as the reason for the full track ("a wrong edit would quietly change how Yantra's steps run"). The acceptance check is the only guard.

**Options.** (1) **Recommended**: keep the table, and add three mechanical checks the coder runs and reports:
   - **the word list is in the brief**: § 5 lists the grep pattern (the § 1.1 values plus BR1-01's categories), so "before" and "after" are the same run and the reviewer can re-run it;
   - **token conservation**: every backticked token that disappears from a generic file (`git diff --word-diff=porcelain` on the eight files, the `-` lines) appears after the change in `CLAUDE.md` § Step workflow or in an `INDEX.md`; a 20-line scratch script, its output in the impl report. A token that is dropped on purpose (an example) is listed with the reason;
   - **the outline is unchanged**: `grep -n '^#'` of each file before and after differs only by the moved index sections and the README's new section. No heading lost, none reordered;
   - and the reviewer's dry run becomes a **round trip per table row**: for each row, the reviewer reads the new generic sentence with the settings entry and writes the Yantra reading in one line; it must say what the old line said. A row where it does not is a finding.
(2) Keep § 5 as written and rely on the reviewer's reading. Cheaper to write, and the faults above stay possible.

### BR1-06 — minor — size and order: the index move is a separable unit, and the coder should be Opus

**Problem.** The brief touches 12 files, several of them long (the skill 711 lines, the README 400, the agents about 900 together). Two concerns are in it that could ship apart (the skill's size rule, `SKILL.md:153-159`): the index move with its tool and test changes (6 files, mechanical, checked by `run-tooling-tests.bat` and a diff of `step-ls.bat`'s output), and the generic rewrite (prose, checked by § 5). The brief says nothing about the order of work or the coder's model.

**Why it matters.** Mixed in one diff, a tool regression hides among 1,000 lines of prose changes; done first, the index move is green before any prose moves. The skill's Opus criteria name "a cross-module refactor, or roughly more than 10 files" (`SKILL.md:306`); this is one, in files where a wrong word changes every later step.

**Options.** (1) **Recommended**: keep one step; § 3 or § 5 states the order: INDEX.md and the tools first, `run-tooling-tests.bat` and the before/after output diff green, then the prose; the brief recommends Opus for the coder. (2) Split: S056a the index move, S056b the prose. Two gates for the user; only worth it if the user wants the index move committed today.

## Nits

- **BR1-07** (nit) § 1.1, row 1: the provenance rule covers "(…, by KLA)" tags. Say the same for the evidence tags that name steps and numbers ("23-10-2026, from S029: …", "S021, 57 files", "first run: S053's power readings", `SKILL.md:96, 153, 160, 458`): they stay as the record of why a rule exists, in every repo.
- **BR1-08** (nit) § Out of scope: say that the 69 past step files that write "README § Index" or "the README index row" (one literal link, `README.md#index`) keep their wording; INDEX.md is one hop from the README's pointer.
- **BR1-09** (nit) § 2: ISO 9001 § 7.5 is right; the part that matches here is § 7.5.3 *Control of documented information*: one controlled version, available where it is used, changes identified. Name the sub-clause, and the "to verify" habit is kept.
- **BR1-10** (nit) § 1.2, the stop message: "docs/steps/README.md lists the entries" — fine; add "(see `## Pre-flight` for the form)" so a new repo copies the shape that works.

## Checked and found consistent

- `docs/steps/README.md`: `## Index` at `:318`, `## Queued` at `:378`, the conventions `:1-317`, as § 1.3 says. `docs/roadmap/README.md`: `## Index` at `:34-37`, an empty table.
- The tools: only `step_facts.py:166` opens the index; `step_ls.py` and `step_stats.py:304` reach it through `gather()`; `step_feedback.py` globs the step folders, `brief_facts.py` and `step_snapshot.py` never read it; no `.bat` names the README. § 6.2 holds.
- Checks 1 and 8 of `step_check.py` keep working after the move: `parse_index`'s regexes and the `## Queued` heading do not depend on the file's name; only the path in `gather()` and the message texts change. `check_folders` compares the parsed folders with `docs/steps/S0*` directories, unchanged.
- `SHARED_DOCS` (`step_facts.py:13`) is used by `step_facts.py`, `step_check.py:193` and `step_ls.py` (the facts file lists them); dropping the README from it means a conventions change shows as an unclaimed working-tree change, which is right once the README is a synced file.
- The agents receive `.claude/CLAUDE.md` as project instructions: this run's context carries it, with `CLAUDE-COMMON.md`, without a read; `coder.md:11` and `code-reviewer.md:25` also name it. The roadmapper and the advisor get it the same way, though their files do not list it.
- The `## Pre-flight` pattern the brief follows: the skill reads the section from the heading to the next `## ` (`pre-flight/SKILL.md:25-26`); `preflight.py:38-39` parses it by heading; the stop message form (`pre-flight/SKILL.md:33-34`) is the one § 1.2 copies.
- No port, URL or host in the eight generic files (the dev-server port `5176` is in `device-checks.md:15`, which stays Yantra's). `/smtw-review` is not named in the skill or the agents; `§ SMTW-Review` is (BR1-01 f).
- The facts file: `SHARED_DOCS` at `step_facts.py:13`, `parse_index` at `:31`, `SEARCH_DIRS` at `brief_facts.py:29`, `YANTRA_TEST_RUN` in six `.bat` files, the two rejected files absent, the two `INDEX.md` absent.
- § 2 standards: the twelve-factor config split and ISO 9001 § 7.5 fit; no maintenance standard applies to a process step, as the brief says.
- Track full: right. Manual checks none: right, no screen changes. The user's U2 decision is reflected in § 1.3, § 3, decision 2 and § 6.
- `docs/steps/device-checks.md:6` links `README.md` § Manual checks, which stays in the conventions.

## Feedback

- hindrance: one wide grep over the eight files returned 31 KB and was saved to a file I had to read back; narrower per-category greps would have cost the same calls with less context (1 run, about 3 minutes).
- idea: `brief_facts.py` could print the heading at a cited `file:line` (`docs/steps/README.md:318` → `## Index`), so a reviewer confirms a line claim without opening the file.
- rule: the brief-reviewer instructions (Plan.MD, the domain docs, the UX checklist) assume an app step; for a process or docs step most of them are void, and no rule says so. I checked Plan.MD for workflow content and found none (one grep, 2 minutes).
