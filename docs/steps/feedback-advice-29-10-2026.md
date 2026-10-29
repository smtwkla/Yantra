Step: none — the step workflow itself (all 125 feedback items, S048–S065)
Doc: advice feedback-system
Author: Advisor (Fable)
Date: 29-10-2026

# What to change in the step workflow so the agents' feedback stops recurring

## 1. Summary: the top 5, by time saved per effort

1. **Fix `step_snapshot.py diff`** (smtw-common): UTF-8 stdout, `-- <pathspec>` pass-through, and leave the step's own `docs/steps/` folder out by default. Eight unread items in two steps (S063 CR r1 ×3, CR r2, S064 CR r1 ×2, CR r2 ×2); every code review since the rounds landed lost 1–2 runs to it. Effort S.
2. **Fix `brief_facts.py` path rows** (smtw-common): resolve a path the brief gives without its folder by suffix (`git ls-files '*/<path>'`), and print one row per file. "No such file" for a file that exists was reported in S048, S059, S061 (all `noted`) and again in S064; the duplicate rows in S057 and S058 (`noted`). Effort S.
3. **Fix `step_feedback.py`** (smtw-common): it cuts 20 of the 125 items at their first line (the agents wrap items at 100 columns), so the log holds half-sentences; and add a `Theme` column with a per-theme count, so a theme `noted` twice is seen as recurring. Effort S.
4. **One shell section instead of three copies** (smtw-common, README): the heredoc rule is broken because its sanctioned path is not written down; the `cmd //c` rule left out "from the repo root"; `&&` chains and `grep` exit 1 are not mentioned. Replace the three agent-file copies with one README section the agents point at, and reword the heredoc ban into "Write the script to the scratchpad, then run it". Effort S.
5. **UI controls in the brief feed the facts run** (smtw-common, `brief_facts.py` + SKILL self-check item 5): a backticked quoted label (`"Print asset list"`) is grepped in the test folders, so a step that hides, renames or moves a control sees the browser tests it breaks before review (S064 BR1-01: 20 lines, then BR2-01: 14 more; about 15 min of review and one red whole-suite run). Effort S–M.

Everything below is verified against the files in this repo as of HEAD `1baae21`; the lines are named. The transcripts `step_stats.py` reads are not on this machine (every agent-hour and token column is 0 here), so cost is weighed by the minutes the items themselves report, not by `/step stats`.

## 2. The table

| # | Recommendation | Evidence (items; recurrences; verified at) | Where | Effort | Expected effect |
|---|---|---|---|---|---|
| 1a | `step_snapshot.py`: `sys.stdout.reconfigure(encoding="utf-8")` before `main` | S064 CR r1, CR r2 (unread); S049 impl "cp1252" `noted`. `step_snapshot.py:360-361` has no reconfigure; `step_feedback.py:122` and `brief_facts.py:258` have it. Simulated here: `PYTHONIOENCODING=cp1252 python -c "print('→')"` raises `UnicodeEncodeError`; with reconfigure it prints | smtw-common `tooling/steps/step_snapshot.py` | S | no run lost per code-review round on Windows |
| 1b | `diff` takes `-- <pathspec>` after its flags; with none, excludes `docs/steps/S0NN-*` | S063 CR r1 (×3), CR r2; S064 CR r1, CR r2 (unread); `step_snapshot.py:332-339`: any extra argument prints `__doc__` and exits 2, which is the "printed help" of S063 CR r2 | smtw-common `step_snapshot.py`, `.claude/agents/code-reviewer.md:25-33` (one sentence), SKILL § Snapshots | S | the verify round reads the fix round's code only; the reviewer reads the brief and the impl report once, not again inside the diff |
| 2a | `brief_facts.check_path`: suffix lookup when the path is not at the root | S048 BR r1, S059 BR r1, S061 BR r1 (all `noted`), S064 BR r1 (unread): 4 steps. `brief_facts.py:161-168` tests `ROOT / ref.value` only; `check_file` (`:171-176`) already does the suffix lookup for bare names. Verified: `git ls-files --cached --others --exclude-standard '*/readings/ReadingsSheet.vue'` → the one file; `'*/jwt/jwks_client.py'` → none | smtw-common `tooling/steps/brief_facts.py` | S | 2–3 false rows per brief gone; a library path reads "not in the repo" instead of "no such file" |
| 2b | one row per file, its line ranges merged | S057 BR r1, S058 BR r1 (`noted`). `extract_refs` (`:90-98`) dedupes on the whole `Ref`, line numbers included | smtw-common `brief_facts.py` | S | shorter facts file |
| 2c | *Code folders* adds the frontend root config files | S055 BR r1 ×2 (`noted`): `DEVICE_ONLY` "not found". Verified: `git grep … -- frontend/playwright.config.js` finds it; `brief_facts.grep` accepts a file pathspec (probe run) | Yantra `.claude/CLAUDE.md` § Step workflow, *Code folders* | S | config constants resolve in the facts run |
| 3a | `step_feedback.py` joins an item's continuation lines; a log row matches the full text or its first line | 20 of 125 items are wrapped and cut (count probe); the log's 97 rows carry the cut text. `step_feedback.py:50-54` matches one line. Probe with the patch: 125 items, 20 joined, still 28 unread | smtw-common `tooling/steps/step_feedback.py` | S | the log holds whole items; nothing already read comes back |
| 3b | `Theme` column in the log; `step_feedback.py --themes` counts rows per theme and names the last decision | `noted` three times, then back: facts path (S048, S059, S061 → S064), cp1252 (S049 → S064 ×2), big diff spilled to a file (S056 BR, S062 s1 → S063 CR, S064 BR r2), CRLF (S055, S056 → S064). A token-match probe (`scratch`-style, see § 5) was too noisy to automate recurrence; a human tag is cheap | smtw-common `step_feedback.py`, SKILL § Feedback; Yantra `docs/steps/feedback-log.md` (a column) | S | recurrence is a number at triage, not a memory |
| 4 | one *Shell on Windows* section in `docs/steps/README.md`; the agents point at it | heredoc: S048, S049, S056, S057, S059, S061, S062 (acted 27-10), S063, S064 again (after the rule); `cmd //c`: S049, S056, S061 (acted), S064 (relative path after `cd`); `&&`+`grep`: S048, S063. The rule is copied in `coder.md:80-87`, `code-reviewer.md:230-233`, `brief-reviewer.md:209-210` with different wording | smtw-common README, three agent files, SKILL § Snapshots line 539-540 | S | one text to fix; the sanctioned path named, so the ban is not broken |
| 5 | backticked quoted text (`"Label"`) is a `ui` ref: grepped in the test folders | S064 BR r1 idea, BR r2 idea, impl idea; S063 BR r1 idea ("Equip Class"): 4 items, 2 steps. The S064 brief has 2 such tokens today, so the convention costs the orchestrator a few backticks. A probe on all quoted/italic texts of the S064 brief gave 160 texts, 76 with hits (`"No"` 157, `"Save"` 132): opt-in by backticks, not a scan, is the right cut | smtw-common `brief_facts.py`, SKILL Phase 1 self-check item 5 | S–M | the orchestrator's own facts run lists the e2e lines a hidden control breaks |
| 6 | *Shared code* entry: a change to `api.js` or `e2e/support/` adds one run of `screens.spec.js` on `phone-webkit` | S064 advice idea (unread); the advice file (`0-advice-fetch-failed-log.md:14-15`) saw the page-leave rejection on WebKit only. Full costs about 2.5 min plus Docker (S055 commit); `screens.spec.js` on WebKit about 160 s (S055 impl) | Yantra `.claude/CLAUDE.md` § Step workflow, *Shared code* and *Browser tests* | S | the WebKit-only fault shows in the step, not in the release |
| 7 | *Browser tests* entry: "the e2e backend writes no access log" | S064 impl idea (unread), 1 round lost | Yantra `.claude/CLAUDE.md` *Browser tests* | S | one red test fewer |
| 8 | `step_feedback.py` prints the unread count at the end already; SKILL § Feedback adds: triage when unread ≥ 20 or every third gate B | 97 items read once on 27-10; 28 unread after two steps | smtw-common SKILL § Feedback | S | triage cadence |

## 3. The tool fixes

### 3.1 `step_snapshot.py` — UTF-8 output, pathspec, own-folder exclude (smtw-common)

*Fact:* `diff()` (`step_snapshot.py:250-261`) runs `git diff base tree` with no pathspec; `main` (`:332-339`) accepts only `--stat` and `--from-round N`, and prints the module docstring for anything else. `git()` decodes with `encoding="utf-8"` and `print()` writes to a cp1252 console on Windows. *Fact:* the probe `scratch`-style script `/tmp/claude-0/-home-user-Yantra/b879817f-aa2a-5c3a-9684-8e0b0d80a5f6/scratchpad/snapshot_patch_probe.py` ran the code below under `PYTHONIOENCODING=cp1252` on this machine, with the four argument forms parsed as expected (output in the run log of this session; the diff was empty because the tree matches HEAD).

```python
def diff(repo, step_id, from_round=None, stat=False, paths=()):
    ...  # base as today
    tree = working_tree(repo, base)
    # The reviewer reads the step's own brief, report and reviews in full anyway (28-10-2026,
    # S064 CR: 2 000 of 5 900 diff lines were those files); a pathspec of its own replaces this.
    pathspec = list(paths) or [".", f":(exclude)docs/steps/{step_id}-*"]
    return git(repo, "diff", *(["--stat"] if stat else []), base, tree, "--", *pathspec)


def parse_diff_args(rest):
    """['--stat', '--from-round', '1', '--', 'backend'] -> (stat, from_round, paths); None when wrong."""
    paths = []
    if "--" in rest:
        cut = rest.index("--")
        rest, paths = rest[:cut], rest[cut + 1:]
    stat = "--stat" in rest
    rest = [a for a in rest if a != "--stat"]
    from_round = None
    if rest[:1] == ["--from-round"] and len(rest) == 2 and rest[1].isdigit():
        from_round, rest = int(rest[1]), []
    return None if rest else (stat, from_round, paths)

# in main():
        if argv[:1] == ["diff"] and len(argv) >= 2:
            parsed = parse_diff_args(argv[2:])
            if parsed is None:
                print(__doc__)
                return 2
            stat, from_round, paths = parsed
            print(diff(repo, argv[1], from_round, stat, paths))
            return 0

# at the bottom, as in step_feedback.py:122:
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
```

*Recommendation:* also pass `errors="replace"` in `git()`'s `subprocess.run`, so a file with a non-UTF-8 byte (a `.bat` with a cp1252 dash) does not raise `UnicodeDecodeError` in the diff. *Assumption:* no such file is in the repo today; the cost is one argument.

Docstring and `.bat` comment: add `[-- <pathspec>…]` to the `diff` lines (`step_snapshot.py:130-131`, `tooling/step-snapshot.bat` line 5). `code-reviewer.md:25-33`: one sentence, "the diff leaves the step's own `docs/steps/` folder out; `-- backend frontend` narrows it further". Unit tests live in smtw-common (`tooling/common/tests`); add one for `parse_diff_args` and one that the default pathspec excludes the step folder.

### 3.2 `brief_facts.py` — suffix match, one row per file (smtw-common)

*Fact:* `check_path` (`brief_facts.py:161-168`) looks only at `ROOT / ref.value`. The brief reviewers' four reports name files that exist deeper (`frontend/src/views/readings/ReadingsSheet.vue`, `frontend/src/stores/auth.js`, `frontend/e2e/equipment.spec.js`, `frontend/src/components/documents/PhotoViewer.vue`); the lookup `git ls-files --cached --others --exclude-standard '*/<path>'` finds each one and nothing for `jwt/jwks_client.py` (run on this machine, § 2 row 2a).

```python
def check_path(ref, folders=None):
    path = ROOT / ref.value
    found = [ref.value] if path.is_file() else suffix_matches(ref.value)
    if not found:
        return [f"- `{ref.value}`: **no such file** (not in the repo: a library path, or new)"]
    if len(found) > 1:
        return [f"- `{ref.value}`: **{len(found)} files end so**: {listing(found)}"]
    path, where = ROOT / found[0], "" if found[0] == ref.value else f" (`{found[0]}`)"
    count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    if ref.last_line > count:
        return [f"- `{ref.value}`{where}: **has {count} lines**, the brief cites line {ref.last_line}"]
    return [f"- `{ref.value}`{where}: exists ({count} lines)"]


def suffix_matches(path):
    """Tracked or untracked (not ignored) files whose path ends in `/path`: the brief often gives a
    path relative to a folder it names in prose (S048, S059, S061, S064 brief reviews)."""
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", f"*/{path}"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return sorted(set(result.stdout.split()))
```

One row per file: in `main()`, before the loop, merge the `path` refs by value, keeping the highest `last_line` (the only thing `check_path` uses), e.g. `merged = {}; for r in group: merged[r.value] = max(merged.get(r.value, r), r, key=lambda x: x.last_line)`.

*Fact (no change needed):* the S058 "`test.fail` treated as `.` any character" item is already fixed by the 27-10 `greppable` change (`brief_facts.py:81-87`): `classify` returns `None` today for `test.fail`, `page.route`, `example.test`, `it.fails` (run on this machine). Log it as `acted` by that change.

### 3.3 `brief_facts.py` — UI controls (smtw-common) and the brief's convention

*Fact:* `extract_refs` reads backticked tokens only (`brief_facts.py:35, 90-98`); a label written `"Print asset list"` or *Print asset list* is never looked up, so S064 § 8.3 missed 34 e2e lines across two review rounds (BR1-01, BR2-01; `2-brief-review-r1.md:18-40`). *Fact:* a scan of every quoted or italic text in the S064 brief gives 160 texts, 76 of them found in `frontend/e2e`, with `"No"` 157 hits and `"Save"` 132 — a scan would be noise (probe `ui_text_probe.py`, this session).

*Recommendation:* opt-in by form. A backticked token that is itself in double quotes, `` `"Print asset list"` ``, is a new `Ref("ui", …)`: `git grep -n -F -e <text>` over the test files only (`is_test_path`), listed as `file:line` with `MAX_LISTED` and the count. The S064 brief has two such tokens today, so the convention costs the orchestrator a few characters per control.

```python
UI_TEXT = re.compile(r'^"([^"\n]{2,60})"$')
# in classify(), first:
    match = UI_TEXT.match(token)
    if match:
        return Ref("ui", match.group(1))
# a check:
def check_ui(ref, folders=None):
    hits = [h for h in grep(ref.value, folders, word=False) if is_test_path(h.split(":", 1)[0])]
    lines = [f"{p}:{l}" for p, l, _ in (h.split(":", 2) for h in hits)]
    return [f"- `\"{ref.value}\"`: in {len(lines)} test line(s): {listing(lines) or '—'}"]
# CHECKS["ui"] = check_ui; SECTIONS gains ("ui", "Screen text in the tests")
```

SKILL Phase 1, self-check item 5 (`SKILL.md:208-214`), one sentence: "A control the step hides, renames or moves: write its label as `"Label"` in backticks, so the facts run lists the browser-test lines that use it; put each line in § Tests." That is a tool and a convention, not a prose rule the agent must remember to grep.

### 3.4 `step_feedback.py` — whole items, a theme count (smtw-common)

*Fact:* `ITEM` (`step_feedback.py:32`) matches one line; the agents wrap long items onto an indented second line (the README and agent files say "one line", the files are wrapped at about 100 columns). 20 of 125 items are cut (count probe); e.g. the S048 BR r1 item ends "…and lost the", the S064 impl items end "the Edit tool's", "I broke it". The log's row key is the cut text, so a fix must keep those 97 rows valid. *Fact:* the probe `feedback_patch_probe.py` with the change below gives 125 items, 20 joined, 28 unread — the same unread count as today.

```python
# in feedback_items(), replace the `item = ITEM.match(line)` block:
        item = ITEM.match(line)
        if item:
            label = item.group(1).lower()
            items.append([label if label in LABELS + ("none",) else "other", item.group(2).strip() or line.strip()])
        elif items and line.startswith("  ") and line.strip():
            items[-1][1] += " " + line.strip()          # a wrapped item goes on
    return [tuple(i) for i in items]
```

A row written before this change holds the item's first line only. So let `feedback_items` return `(label, text, first_line)` and test `item_key(step, name, text) not in keys and item_key(step, name, first_line) not in keys`. The docstring (`:10-11`) then says "an item may continue on indented lines".

**Theme column.** Add a fifth column `Theme` to `log_row` (empty, for the orchestrator), and `--themes`: read the log, count rows per theme, print `theme: N items, decisions: noted ×3, acted ×1 (last 27-10-2026)`. Themes are short tags KLA or the orchestrator writes at triage (`shell-heredoc`, `facts-path`, `snapshot-diff`, `cp1252`, `big-diff`, `crlf`). The tool counts and judges nothing, as the others do. *Fact:* an automatic recurrence match on shared backticked names was tried here (`recur_probe.py`): `diff` and `file` link everything, `heredoc` links the right six; it is not reliable enough to ship, and a tag at triage costs five seconds per row.

## 4. Rules to remove, merge or reword

| Rule | Where | The conflict | Change |
|---|---|---|---|
| "write multi-line text … never through a heredoc, `echo` or `python -c` with quotes" | `coder.md:82-83`; `code-reviewer.md:232-233` "write nothing through a heredoc" | Broken in S063 and S064 after it landed (27-10 22:24, `c9142b4`), by the coder's own account: a one-off Python fix has no sanctioned path. The S064 coder asked for a `tooling/replace.py` — a tool to avoid a rule | Reword to the path that worked every time the agents reported (S056, S057, S061, S063): "A script or multi-line text goes to a file first (`Write` to the session scratchpad or `scratch/`), then `uv run --no-project python <file>`. No heredoc, `echo` or `python -c` with the text inline." One sentence, and it names what to do |
| `cmd //c "tooling\run-tests.bat …"` | `coder.md:84-85`, `code-reviewer.md:230-231`, `brief-reviewer.md:209-210`, SKILL `:539-540` (says the opposite for the snapshot: call the `.py` directly) | S064: the relative path failed after an earlier `cd`; S048 CR r2: `MSYS_NO_PATHCONV=1` needed for `refs/steps/S048:<path>` | One section, README § *Shell on Windows (Git Bash)*: (1) `.bat` wrappers: `cmd //c "tooling\x.bat …"` from the repo root — `cd` to it in the same command; a Python step tool: `uv run --no-project python tooling/steps/x.py …` directly; (2) scripts and multi-line text: a file first (above); (3) chain read-only commands with `;`, not `&&`: `grep` exits 1 on no match (S048, S063); (4) `MSYS_NO_PATHCONV=1` before a git argument with a `/` that is not a path (`refs/steps/S0NN:<file>`); (5) read the summary line before calling a run green. The three agent files keep one line: "Shell: README § Shell on Windows." |
| "one-line items" in `## Feedback` | the four agent files, README `:45-47` | The files are wrapped at about 100 columns, so 20 items span two lines and the tool cut them | After 3.4, say "one item per bullet; it may wrap" — or leave the text and let the tool cope. The tool fix is enough |
| Round-2 tests "the repo's command for all suites" | `code-reviewer.md:155` | S049 CR r2 (`noted`): a fix round that touched `tooling/` only still asks for all suites | Reword: "the suites of what the fix round changed; all suites when it changed code outside one suite's folder". One clause |
| Brief reviewer checks Plan.MD, domain docs, UX list for every step | `brief-reviewer.md:50-54, 87-119` | S056 BR r1 (`noted`): void for a process or docs step | One line at the top of *What to check*: "A step with no screen and no business rule (tooling, docs, process): skip *Standards*, *Use on the floor* and the product plan unless the brief cites them." |
| "A plain `git diff <ref>` lists them as deleted" + the pathspec idea in the spawn prompt | SKILL `:336-342`, `code-reviewer.md:25-33` | S062 CR r1 idea asked the orchestrator to list non-step files in the prompt; 1b makes the tool do it | After 1b, drop the idea of an exclude list in the prompt; the prompt names `diff S00N [--from-round n]` only |

Nothing here adds a rule; the shell section replaces three copies and the SKILL line with one text.

## 5. The feedback system: findings and the change

*Facts:*
- 125 items; 97 read on 27-10-2026: 86 `noted`, 11 `acted` across 4 changes, 0 `dropped`. `noted` items came back as new items in later steps in five themes (facts path 3→1, cp1252 1→2, big diff 2→2, CRLF 2→1, duplicate facts rows 2→0 so far). `noted` is "read, no change" by the skill's definition (`SKILL.md:519-521`), and it produced no change in any of these five.
- The one `acted` theme that came back is the heredoc rule (S063, S064): the change was a prose ban, and the ban had no path to follow (§ 4).
- The tool cuts 20 items (§ 3.4); the log holds half-sentences for them.
- The 5-item / 4-label form works: items carry minutes and file names; `idea` (43) and `hindrance` (47) are the useful labels; `rule` (11) found three real conflicts (S056 D6, S057 § 5, S062 D-1, S064 heredoc). No change to the form.
- Gate-time reading (`SKILL.md:511-513`) cannot be verified here: the orchestrator transcripts are not on this machine. The two-step gap between triages (97 items, then 28) says the gate line did not lead to a change by itself.
- Items are written per file, so a theme spans many rows; the tool has no grouping, and an automatic grouping was too noisy in a probe (§ 3.4).

*Recommendations:*
1. **`noted` gets a count.** The log's `Theme` column and `--themes` (§ 3.4). Rule, one line in SKILL § Feedback: "A theme with two `noted` rows is decided at the next triage: `acted` or `dropped`; `noted` is not available for it." The decision then costs KLA one line; recurrence stops being free.
2. **`dropped` is used.** Several `noted` rows are really drops with a reason the agents should see (the Write tool refusing a scratchpad draft is a harness limit; the `claude.exe` search was a one-off). A `dropped: <reason>` row tells the next agent not to write it again if the orchestrator quotes the log's recent drops in the spawn prompt — a cheap addition to § Feedback: "the spawn prompt names the themes dropped in the last triage".
3. **Triage cadence** by the number the tool already prints (`step_feedback.py:114`): the gate B report says "feedback: N unread" and proposes `/step feedback` at ≥ 20. One line in SKILL § Phase 2 step 4 and § Feedback.
4. **Fix tools before writing rules**: of the 4 changes acted on 27-10, the two tool changes (snapshot rounds, `greppable`) ended their themes; the prose change (shell rules) did not. That is the pattern to keep.

## 6. What not to do, and why

- **A `tooling/replace.py <spec.json>` that keeps line endings** (S064 impl `rule` item): a second editing tool beside Edit/Write, with its own spec format; the real fix is the sanctioned path (§ 4). *Assumption:* the Edit tool on Windows keeps a file's existing CRLF when the old text is matched exactly; KLA can check this once (§ 8 Q3). A CRLF/LF counter helper (S056 idea) likewise: `file` and `git diff --stat` show it, and the README § IDE reformatting already says to use Edit, not `sed -i`.
- **A snapshot of the before-state, or the coder recording hashes** (S056 CR r1 idea): the round refs (27-10) cover the fix-round case; the gate B snapshot covers the step. Nothing left to build.
- **A sibling-repo facts option** (S057 BR r1): reads outside the repo; one lift step a month does not pay for it.
- **`step_stats --compare-with`** (S057 CR r1): the stats always differ by the step's own transcript (the S057 `rule` item said so); a test fixture in smtw-common is the right place, and it exists there.
- **Headings checked by `brief_facts.py`** (S058 BR r1), **a count-of-phrase check** (S056 BR r2), **route "asserts exact lists" hints** (S061 BR r1): each is one step's need; the facts file would grow for every brief. Drop with the reason "one use".
- **"Verified in code" line per rule in the brief** (S064 BR r1): self-check item 1 (`SKILL.md:184-190`) already asks for `file:line` beside every claim, and the brief reviewer's job is to not trust the brief (`brief-reviewer.md:55-56`). A second line per claim doubles the brief; the facts run is the shared evidence. Instead, enforce item 1 as it stands.
- **A whole-suite run at Full for every `api.js`/`support/` change** (S064 advice idea, as written): Full needs Docker Desktop for the iPhone container; a coder without it stops with QUESTIONS. Row 6 of § 2 is the smaller version: `screens.spec.js` on `phone-webkit` only (about 160 s), stated in *Shared code*.
- **A console allow for "fetch failed"** (S064 impl idea): superseded by S065, which removed the `allowBrowserError("fetch failed")` lines (`S065 1-brief.md:53`). Drop.

## 7. Proposed decision per unread item (rows for `docs/steps/feedback-log.md`)

Rows as `--rows` printed them (the item cell is the key), with the decision filled. If the `Theme` column is adopted, append it as a sixth cell.

| Step | File | Label | Item | Decision |
|---|---|---|---|---|
| S063 | 2-brief-review-r1.md | hindrance | a Bash call chaining several `grep`s with `&&` stopped at the first empty result, so one batch had to be re-run with `;` (1 run, 2 min). | acted: README § Shell on Windows, point 3 (chain with `;`) — § 4 |
| S063 | 2-brief-review-r1.md | idea | the facts file could list, for each masters section label the brief names ("Equip Class"), where the e2e specs use it; I grepped `masters.spec.js` and `screens.spec.js` by hand for the section loop. | acted: `brief_facts.py` `ui` refs for backticked `"Label"` — § 3.3 |
| S063 | 3-impl-report.md | hindrance | Bash heredocs that held Python with `'` inside a `'''` string or `\n` inside JSON failed twice ("unexpected EOF", a count of 0); a script file written with the Write tool worked each time (about 4 min lost). | acted: the shell rule names the path (a file first, then run it) — § 4 |
| S063 | 3-impl-report.md | idea | `tooling/steps/brief_facts.py` could flag a "new" shared test helper (fixture, `e2e/support/` export) the brief does not name, since a `support/` change re-runs the whole browser suite. | dropped: the impl report's file list and the code reviewer's *Shared code* check already show a `support/` change; a facts-run flag needs the diff, which the facts run does not read |
| S063 | 4-code-review-r1.md | hindrance | `step_snapshot.py diff S063` takes no path filter, so reading only the step's files among the roadmap and tooling changes in the same snapshot needed a plain `git diff refs/steps/S063^ refs/steps/S063 -- <files>` (2 calls). | acted: `diff … -- <pathspec>` and the default exclude of the step's own folder — § 3.1 |
| S063 | 4-code-review-r1.md | waste | the one-line `TABS` JSON of `docs/schema.html` made a docs diff 52 KB and spilled to a file; a grep of the tables was needed instead (1 extra call). | noted (theme big-diff, 3rd row): with § 3.1 the reviewer runs `diff S0NN --stat` first and `-- docs/schema.md` for the schema; `schema.html` is read by its `TABS` grep. Decide at the next triage if it returns |
| S063 | 4-code-review-r1.md | idea | let `step_snapshot.py diff` take `-- <paths>`, and have the orchestrator's spawn prompt give the list of non-step files in the snapshot as an exclude list. | acted: the pathspec, § 3.1; the exclude list in the prompt is not needed (the tool excludes the step's folder) |
| S063 | 4-code-review-r2.md | waste | the first `diff --from-round 1` with a `--` path list printed the tool's help text instead of the diff, so I made one more full run of the diff and filtered it myself (1 run). | acted: `parse_diff_args` accepts `--` after the flags — § 3.1 |
| S064 | 0-advice-fetch-failed-log.md | waste | my first `fetch-on-leave.cjs` run returned the fetch promise from `page.evaluate`, which waited for it, so case A showed "ok 200" on both engines; one re-run after the fix (2 min). | dropped: the advisor's own experiment design; no workflow change |
| S064 | 0-advice-fetch-failed-log.md | hindrance | WebKit's exact source line for "Load failed" on a cancelled load was not findable by web search; only the `FetchResponse.cpp` fallback string turned up (3 fetches). | dropped: a research limit, not the workflow's |
| S064 | 0-advice-fetch-failed-log.md | idea | the shared-code rule in CLAUDE.md § Step workflow could say that a change to `api.js` or `support/` runs the whole suite at Full once, since only `phone-webkit` shows a page-leave rejection. | acted (smaller form): *Shared code* adds one run of `screens.spec.js --project=phone-webkit` for a change to `api.js` or `e2e/support/` — § 2 row 6; KLA decides (§ 8 Q2) |
| S064 | 2-brief-review-r1.md | idea | `brief_facts.py` reported `readings/ReadingsSheet.vue`, `router/index.js` and `stores/auth.js` as "no such file" because the brief gives the folder in prose ("in `frontend/src/views/`"); resolving a trailing path against the code folders would cut three false rows (`scratch/brief-facts-S064.md:32,63,66`). | acted: `check_path` suffix lookup — § 3.2 (4th report of this theme; S048, S059, S061 were `noted`) |
| S064 | 2-brief-review-r1.md | idea | the facts file lists tests by code name, not by UI control; for a step that hides or renames controls, a grep of `frontend/e2e` for the aria-labels and button names the brief names (here *Print asset list*, `Select … for labels`, `Tickets`, `Category`) would have surfaced BR1-01's twenty lines in the orchestrator's own run (6 greps, about 10 minutes in this review). | acted: `ui` refs and self-check item 5 — § 3.3 |
| S064 | 2-brief-review-r1.md | hindrance | a 27-item brief needs about 40 file reads to verify its claims; most time went to the claims that turned out false (BR1-02, BR1-04, BR1-09). A § "Verified in code" line per rule, saying which file:line the orchestrator opened, would let the reviewer skip the ones it did. | dropped: self-check item 1 already requires `file:line` per claim; the reviewer's job is to verify, not to trust a "verified" line — § 6 |
| S064 | 2-brief-review-r2.md | hindrance | the prompt's baseline (`c9142b4 + uncommitted S063`) did not match the tree (`0e4d215` is S063's commit); `git rev-parse` and `git status` settled it in one call, but the brief's `Baseline:` carries the stale value too (1 check). | noted: an orchestrator slip; `step_check.py:92-99` already flags a Baseline not in history, and the reviewer writes its own `Reviewed against:` |
| S064 | 2-brief-review-r2.md | idea | for a step that hides or folds controls, the orchestrator's grep of `frontend/e2e` should include every control the brief moves, not only the ones it hides — here `Filter by property`, `Level`, `Lifecycle`, `thead` found 14 more lines than § 8.3 lists (3 greps, 5 min). | acted: self-check item 5 says "hides, renames or moves" — § 3.3 |
| S064 | 2-brief-review-r2.md | waste | the diff output (51 KB) exceeded the tool's inline limit and had to be read from the saved file; a `--stat` first and then per-section diffs would have cost less (1 extra read). | noted (theme big-diff, 4th row): the reviewer's own call order; a `--stat` first is already the agent file's advice (`code-reviewer.md:26-27`) |
| S064 | 3-impl-report.md | hindrance | line endings differ from file to file (CRLF and LF mixed); the Edit tool's | noted (theme crlf, 3rd row): see § 8 Q3; after the shell section says "Edit, never `sed -i`", decide at the next triage |
| S064 | 3-impl-report.md | rule | "never a heredoc for multi-line text" conflicts with quick one-off Python fixes. I broke it | acted: the rule reworded to name the path (a file first) — § 4; no `replace.py` (§ 6) |
| S064 | 3-impl-report.md | hindrance | a Bash line with many `$(grep …)` substitutions was refused by the safety check | dropped: a harness safety limit; the agent's move to a script is the right one and the shell section names it |
| S064 | 3-impl-report.md | idea | brief § 8.3 should come from a grep of the e2e specs for the roles a visibility change | acted: covered by § 3.3 (a role name such as `"operator"` in backticked quotes is grepped the same way) |
| S064 | 3-impl-report.md | idea | the e2e backend writes no access log, which a browser test of the access-log card can only | acted: one clause in Yantra's *Browser tests* entry — § 2 row 7 |
| S064 | 3-impl-report.md | hindrance | `cmd //c` inherited the Bash tool's earlier `cd`; a relative `tooling\run-e2e-tests.bat` failed once because I was in `frontend/` (1 run). | acted: the shell section says "from the repo root, `cd` in the same command" — § 4 |
| S064 | 3-impl-report.md | idea | a known console-allow for "fetch failed" in `e2e/support/console.js` would save each offline test two `allowBrowserError` lines. | dropped: superseded by S065, which removed those lines |
| S064 | 4-code-review-r1.md | hindrance | `step_snapshot.py diff S064` crashed with `UnicodeEncodeError` (cp1252, "→" in a brief) when its output went to a file; `PYTHONIOENCODING=utf-8` fixed it (1 run lost). | acted: `sys.stdout.reconfigure(encoding="utf-8")` in `step_snapshot.py` — § 3.1 |
| S064 | 4-code-review-r1.md | idea | `step_snapshot.py diff` could take `--exclude docs/steps/` (or code folders only), since 2 000 of its 5 900 lines were this step's own brief, audit and reviews. | acted: the default exclude of `docs/steps/S0NN-*` — § 3.1 |
| S064 | 4-code-review-r2.md | hindrance | `step_snapshot.py diff S064 --from-round 1` crashed again with `UnicodeEncodeError` (cp1252) when its output went to a file. `PYTHONIOENCODING=utf-8` fixed it, the same as in round 1 (1 run lost; the tool should reconfigure stdout to UTF-8). | acted: as above |
| S064 | 4-code-review-r2.md | idea | `step_snapshot.py diff` takes no path filter, so a verify round reads the impl report and the previous review inside the diff. A `-- <paths>` option, or leaving `docs/steps/` out by default with `--from-round`, would shorten it. | acted: as above |

Also two rows already in the log to re-decide, because the fix exists: the S058 BR r1 `test.fail` item (`noted`) is `acted` by the 27-10 `greppable` change (verified § 3.2); the S055 BR r1 `DEVICE_ONLY` pair (`noted`) becomes `acted` with § 2 row 2c.

## 8. Open questions for KLA

1. **Default exclude in `diff`: the step's own folder, or all of `docs/steps/`?** (a) The step's own folder `docs/steps/S0NN-*` — recommended: a parallel step's files in the same snapshot still show, so the reviewer sees them as "not mine" instead of missing them. (b) All of `docs/steps/` — shorter, but hides a device-check row or an INDEX change the step made. (c) No default, pathspec only — the reviewer must remember the pathspec each time.
2. **WebKit run on a shared frontend change** (§ 2 row 6): (a) `screens.spec.js --project=phone-webkit` once, about 160 s, needs Docker Desktop running — recommended; a coder without Docker returns it as a QUESTION, as the rules say. (b) The Full level — 2.5 min plus the same Docker need, more than the fault needs. (c) Leave it to the release — the fault is found after gate B, as in S064/S065.
3. **Line endings (CRLF theme, 3 reports, all `noted`)**: on your machine, run once: `git config core.autocrlf` (expected `true`) and `git ls-files --eol | grep -c "w/lf"` in the repo root; a count above 0 names working-tree files in LF that an agent's Write wrote. Options: (a) add a `.gitattributes` with `* text=auto` so git normalises on commit, and let Edit keep each file as it is — recommended, one line, no tool; (b) a `tooling` helper to count or convert endings — one more tool for a symptom; (c) leave it. I could not test Windows Edit behaviour from Linux.
4. **The `Theme` column**: (a) add it to the log and tag the 97 rows for the six themes named here (about 25 rows, 10 minutes) — recommended, so `--themes` shows the counts from day one; (b) tag new rows only.
5. **Where the shell rules live**: (a) `docs/steps/README.md` § Shell on Windows, agents point at it — recommended (one synced file, read by every agent already); (b) `CLAUDE-COMMON.md` § Shell preference, which already has one paragraph on PowerShell — also synced, but loaded into every session's context, including non-step work.

## Feedback

- hindrance: the feedback tool cuts 20 of 125 items at their first line, so the themes had to be read from the source files again (8 `awk` reads, about 5 min) — fixed in § 3.4.
- waste: `step_stats.py` shows 0 agent hours and 0 tokens on this machine (the transcripts live on KLA's laptop), so the cost weighting the task asked for could not use it (1 run, the per-step table unused).
- hindrance: the prompt's constraint "edit no file" meant each proposed tool change was verified through a scratchpad wrapper that imports the module (`snapshot_patch_probe.py`, `feedback_patch_probe.py`), about 10 min; a `scratch/` copy of the module would have needed `ROOT` patched too.
- idea: `step_feedback.py --new` could print the step's date beside each item (the brief's `Date:`), so "after the rule landed" is readable without `git log` (1 extra command here).
- rule: the agents' "one line each" for feedback items and the files' 100-column wrapping contradict each other; the tool should accept the wrap (§ 3.4), not the agents the rule.
