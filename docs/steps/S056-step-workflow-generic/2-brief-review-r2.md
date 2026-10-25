```
Step: S056 — The step workflow names no repo
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 82997ee (the working tree holds only S056's own folder and its one README index row; no other step is uncommitted)

**Verdict: no `blocker` or `major` finding is open.** Two `minor` findings, both on the new checks in § 5 (the word list misses values of the two tables; the token-conservation rule contradicts the rows that drop a token on purpose). Three nits. Facts file `scratch/brief-facts-S056.md` (rerun on this draft) was given and used. Full track, round 2.

**What I re-read** (round 2 rule): § 1.1's "Further categories" table a–l and the "Also stays" note; § 1.2 (the form, `none`, the `:11` bullet); § 1.3 (the shape paragraph, the sorted reference list); § 3's `CLAUDE.md` row; § Out of scope (past step files); § 2 (ISO 9001 § 7.5.3); § 5 in full; § 6 Q3; the Review log. I did not re-review § 1.4, § 4 or the rest of § 1.1's first table.

**Every accepted answer of round 1 is in the brief's text**, not only in the Review log: BR1-01 (the a–l table, § 6 Q3), BR1-02 (the sorted list with the git-index exceptions; § 3's `CLAUDE.md` row now says "no index reference to change"), BR1-03 (the shape in § 1.3), BR1-04 (the entry form, `none` with its consequence, the `:11` bullet moved), BR1-05 (word list, token conservation, outline, round trip), BR1-06 (order of work, Opus), BR1-07 ("Also stays"), BR1-08 (Out of scope), BR1-09 (§ 7.5.3), BR1-10 (the stop message).

**Every `file:line` cited in the a–l table and in § 1.3 holds at 82997ee.** I printed each one (`git show 82997ee:<file> | sed -n`): the 48 lines of rows a–l, the 30 index references of § 1.3, the git-index exceptions (`SKILL.md:519`, `step_snapshot.py:10, 13, 93-102, 123`, `step-snapshot.bat:3`), `CLAUDE.md:11` (the *Step workflow* bullet), `step_facts.py:13, 166`. None is off by a line.

## Findings

### BR2-01 — minor — § 5's word list misses values of the two tables it says it covers

**Problem.** § 5 says the list is "the values of § 1.1's two tables", fixed so that before and after are the same run. These table values are not in it (hits are case-insensitive counts over the eight prose files at 82997ee):

| Row | Missing words | Hits |
|---|---|---|
| Table 1, *Browser tests* | the level names `Basic`, `Normal` (`Full` alone is too common; grep `Full level`) | 16, 17 |
| Table 1, *Shared code* | `router`, `auth store` | 2, 1 |
| Table 1, *Device checks* | `laptop`, `TEST machine` | 3, 2 |
| Table 1, *Standards* ("TPM, ISO 14224, EN 13306, …") | the rule at `brief-reviewer.md:85` also names `ISO 55000`, `SMRP`, `ISO 27001` | 2, 2, 3 |
| b | `worker`, `blank`, `open(seed)`, `Pillow`, `urllib`, `QR`, `devops`, `cron` | 2, 4, 1, 1, 1, 6, 3, 1 |
| c | `push or email` | — |
| g | `test_tickets_core`, `tickets-work`, `views/` | 1, 1, 1 |
| h | `camera`, `paper`, `ruler`, `keyboard` | 3, 3, 1, 4 |
| l | `learning maintenance` | 3 |

**Why it matters.** A word not in the list is not in the before/after run, so a line of rows b, h or l left in a generic file passes the check. Token conservation does not catch these: most of them are prose, not backticked (`camera`, `worker`, `learning maintenance practice`).

**Options.**
- (1) **Recommended**: add the words above to the list in § 5. The coder's "grep after" already lists what is left and why, so extra hits on generic words (`paper`, `blank`) cost one line each.
- (2) Keep the list and say the a–l table is checked by the round-trip dry run only. Cheaper, and the mechanical check misses eight of the twelve rows.

### BR2-02 — minor — § 5's token-conservation rule contradicts the rows that drop a token on purpose

**Problem.** § 5 says: every backticked token that disappears from a generic file "appears after the change in `CLAUDE.md` § Step workflow or an `INDEX.md`". The a–l table plans drops with no new home: row g ("the example becomes generic … or is dropped": `tests/test_tickets_core.py`, `e2e/tickets-work.spec.js`, `frontend/src/views/`), row i (the agents' "Yantra"), row j (`by KLA` in the roadmap header template, inside a code block), row l ("learning maintenance practice", dropped). Round 1's option carried the clause "a token that is dropped on purpose (an example) is listed with the reason"; the brief's text left it out.

**Why it matters.** As written, the check fails on the first run, and the coder decides alone whether to restore the token, invent a settings entry for it, or ignore the failure.

**Options.**
- (1) **Recommended**: add to the bullet: "A token dropped on purpose (rows g, i, j, l) is listed in the impl report with its row and the reason; any other missing token is a fault."
- (2) Make every drop a move: each example goes to a settings entry. Over-engineering; nobody needs `tests/test_tickets_core.py` as a setting.

## Nits

- **BR2-03** (nit) § 5, the token-conservation, outline and round-trip bullets: "the reviewer" means the code reviewer there, and "the reviewer" in § 1.1 and § 1.3 means the brief reviewer. Write "the code reviewer" in § 5 (one term, one thing).
- **BR2-04** (nit) § Out of scope: at 82997ee the phrases "README index row", "README index" and "index row" occur in 68 past step files, and no file holds a literal `README.md#index` link (my round-1 count was wrong there; `grep -rni "#index" docs/ .claude/` finds nothing outside S056). Write "about 70 past step files" and drop the link.
- **BR2-05** (nit) § 5, "The grep after": the word list carries `frontend/` and `backend/`, and row k keeps the stack. Say that row k's words (`frontend/`, `backend/`, `uv run`, Bootstrap) are expected leftovers too, so the coder does not try to remove them.

## Checked and found consistent

- **§ 1.2 and `## Pre-flight`**: `.claude/CLAUDE.md` has `## Pre-flight` at `:33` in the form `- **<Entry>**: <value>` (*Test command*, *Tests a clean copy of HEAD*, *Failure logs*, *Re-run failing tests*, *Known fault*); `preflight.py:39` `SECTION = "## Pre-flight"`, parsed by heading at `:68`; the stop message form at `preflight.py:46` and `pre-flight/SKILL.md:33` is the one § 1.2 copies. The *Step workflow* bullet is `CLAUDE.md:11`, as § 1.2 and § 3 say.
- **Row e's pointer**: `CLAUDE.md` § Pre-flight's *Test command* is `tooling\release-tests.bat`, so "a pointer to `CLAUDE.md` § Pre-flight" for the release level holds.
- **§ 1.3's "17 times"**: `docs/steps/README.md` is named 1 (CLAUDE.md) + 1 (advisor) + 5 (brief-reviewer) + 2 (code-reviewer) + 4 (coder) + 2 (roadmapper) + 2 (skill) = 17 times.
- **The domain words outside the tables**: `ticket` and `equipment` have 44 and 35 hits over the eight files; 43 of them are in the README's index rows (which move to `INDEX.md`), the rest are the coder's sample paths (row g) and the LOCK ORDER line (table 1). No category is missing from a–l.
- **The index tools**: `step_facts.py:166` is the only read of the index; `SHARED_DOCS` at `:13` is `("docs/steps/README.md", "docs/steps/device-checks.md")`, so § 1.3's new value replaces the first entry; `step_check.py:8, 53, 137, 140` are the four "README row" messages; `test_step_facts.py:12` is the fixture `README = """…` and `:217` asserts "has no README row". § 6.2 holds.
- **§ 2**: ISO 9001:2015 § 7.5.3 is *Control of documented information* (availability where needed, protection, version control, distribution and changes); the paraphrase is right.
- **§ 6 Q3**: the recommended option matches row a of the table and round 1's option 2a; the alternatives are the ones round 1 gave; KLA decides at gate A.
- **Track, model, checks**: full track right; the coder Opus (the skill's criterion at `SKILL.md:306`, more than 10 files); manual checks none, right for a docs step.
- **Facts file**: the two `INDEX.md` absent, the rejected `.claude/step-settings.md`, `.claude/step-workflow.md` and `docs/ux-checklist.md` absent, every cited tool and agent file present.

## Feedback

- hindrance: the copy of `.claude/CLAUDE.md` loaded as project instructions is older than the file on disk (no *Pre-flight* bullet at `:24`, no `## Pre-flight` at `:33`, the *Step workflow* bullet without `/step feedback`), so I had to grep the file to confirm the brief's main pattern (1 run).
- idea: the facts run could count the hits of a phrase the brief cites with a number ("69 past step files", "named 17 times"), so a count copied from a review is checked by a tool, not by the next reviewer (BR2-04 came from such a copy, one of my own).
