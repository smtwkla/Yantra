# Why first-draft briefs get findings: patterns from S001–S027

Result: no brief review ever raised a blocker. The cost is 61 majors, 347 minors and 241 nits over all rounds (649 findings, 73 review files). The 61 majors fall into a few repeating causes. The top four are: a claim about code or a tool that nobody checked (13), a permission or identity path left open (11), a rule or edge case left to the coder (9), and lock/transaction design (6).

Method and limits:
- Facts: heading counts come from every `2-brief-review-*.md` (rounds r, A1 amendments, staleness s). 45 of the 61 majors came in round 1; the rest came in later rounds on revised text.
- The 61 majors were classified by hand, by title and body. The 347 minors and 241 nits were classified by title keywords, so treat their counts as roughly plus or minus 15 percent.
- Round 1 draft quality and revision quality are both planner output. Later-round findings often come from edits that fixed one finding and left the old text elsewhere.

## 1. Root-cause table (weighted: major 3, minor 1; blocker 0 in briefs)

| # | Root cause | Major | Minor | Nit | Weighted |
|---|---|---:|---:|---:|---:|
| C4 | Rule or edge case left open to the coder (behaviour, state, defaults, wire format) | 9 | 94 | 106 | 121 |
| C1 | Claim about code, library, browser or environment not verified | 13 | 37 | 9 | 76 |
| C5 | Tests: existing tests broken and not named; test cannot be set up; harness order | 4 | 51 | 24 | 63 |
| C3 | Permissions, scope and identity paths (self-grant, key at which site, no-header user) | 11 | 25 | 7 | 58 |
| C10 | UI on a phone: dialogs, taps, defaults, where a control lives, wording | 0 | 50 | 29 | 50 |
| C2 | Locks and transactions (order, what is checked under the lock, snapshots) | 6 | 22 | 5 | 40 |
| C9 | Process, tooling, deploy and device checks (who, where, which network) | 3 | 19 | 11 | 28 |
| C7 | Earlier decision, Plan.MD or an earlier step conflicts; text stale after a revision | 6 | 9 | 16 | 27 |
| C6 | Migration and schema (ENUMs, columns, preconditions, upgrade test DB) | 2 | 17 | 9 | 23 |
| C8 | DB down, worker retry contract, health/startup hooks | 5 | 7 | 1 | 22 |
| C11 | Standards cited wrongly or not at all | 1 | 16 | 24 | 19 |
| C12 | Step too large for one review | 1 | 0 | 0 | 3 |
| | Total | 61 | 347 | 241 | |

Reading the table:
- C4 is the biggest by volume but mostly minor. Each item is small; together they cost the most review time. Reviews say "the coder would otherwise decide alone" about 93 times.
- C1, C3, C2 and C8 carry most of the majors. They are the ones that would have shipped a real defect.
- C11 is almost all minor and nit, but it repeats in most review files. One habit fixes it.

## 2. Top categories: example IDs and a one-minute check

**C4. Rule or edge case left open.**
- Examples: S018 BR1-01 (send-back intensity rule incomplete), S021 BR2-01 (*Down again* fires only if intensity changes), S024 BR1-03 (dialogs "unscoped"), S021 BR1-03 (no "user menu" exists).
- Check: Give every input (field, setting, query key, button) four cells: missing, empty, wrong type, boundary. Any blank cell is a decision you owe.
- Check: For every state change, list actor x current state x already-in-target-state. For every notification or event, name the code line that writes it and whether that path always runs.
- Check: For every phrase like "the user menu", "the list", "the card", open the router and a layout file and name the real file where it lives.

**C1. Unverified claim.** The reviewer ran code, read a library or opened a file and found the draft wrong.
- Examples: S014 BR1-01 (QR version 4, not 3, at level Q), S009 BR1-01 (Bootstrap does not nest modals), S007 BR1-01 (Bootstrap handles Esc with `keyboard: false`), S022 BR1-01 (SBOMs change on every run), S025 BR3-01 (db-server already takes the dumps), S006 BR2-01 (compose working tree differs from HEAD).
- Check: List every sentence that says "X does Y" about code you did not open this session. Write `file:line` beside each, or run a 3-line `uv run python -c` snippet.
- Check: For each external system the brief names (devops repo, compose, Keycloak, cron job), grep it for an existing job or setting that already does the work.
- Check: For each API field a screen shows, grep the endpoint's SELECT and serializer for that field (S003 BR1-01).

**C5. Tests.**
- Examples: S008 BR1-01 (list tests cannot pass against the session DB), S013 BR1-02 (gate runs before `g.user` in tests), S025 BR1-03 (no DB to build the v5 schema), S016 and S018 BR1-04 (`test_role_matrix` breaks).
- Check: Grep tests and frontend specs for each changed symbol or key. List the hits by file and test name in the brief.
- Check: Always grep `test_role_matrix`, `conftest.py` `_TABLES`, the `db_down` fixture and `test_migration_*` for the files you touch. These four names recur in more than 20 review files.
- Check: For each new test, name its fixture and ask whether rows already in the session DB change the result.

**C3. Permissions and identity.**
- Examples: S017 BR1-01 (documents routes hard-code `equipment:edit`), S024 BR1-01 (no header runs as admin), S011 BR2-01 (the "every unit" shortcut fails open for IT admin with a membership), S010 A1-01/A1-02 and S011 A1-02 (`active` is an access switch; login set to your own name), S023 BR1-01 (list scoped to the wrong key).
- Check: For every route and button the draft adds or reuses, write its permission key and whether it is in `SITE_SCOPED`. Grep the reused route for `require_perm` to see the key it really demands.
- Check: For every editable field ask "can this change who can log in or what they see?" If yes, list actor = target, normalised names and inactive people.
- Check: State what a request with no identity gets. The answer is "nothing", never admin.

**C10. UI on a phone.** 50 minors, no major; the most common finding on screen steps.
- Examples: S018 BR3-02 and BR3-09 (single-tap destructive controls; dialogs with nothing required), S018 BR4-02 (disabled-button reason invisible on a phone), S020 BR1-06 (taps that can be defaulted), S027 BR1-02 (*Add note* at the bottom of a long page).
- Check: For each dialog write the composable and its exact call (what `blank` returns), the fields that can be defaulted, the one-tap path for the common case, and where the reason shows when a button is disabled.
- Check: Walk the screen at 360 px in your head: which control is under the thumb, which is below the fold.

**C2. Locks and transactions.**
- Examples: S002 BR1-01, BR1-02, BR2-01, BR2-02, BR3-01 (counter rule, deadlock, REPEATABLE READ snapshot), S012 BR1-01 (lock order cannot derive the type), S017 BR1-03 and S019 BS1-01 (shared locks taken through foreign keys).
- Check: Write one numbered lock sequence per route: table, row, mode (`FOR UPDATE` or shared via FK). Compare it with the LOCK ORDER notes in `tickets.py` and `masters.py`. A different order is a deadlock edge.
- Check: Mark the first plain `SELECT` in the transaction. Decide only from columns of a locking read, never from a plain read after it.
- Check: A counter or "never reused" rule says which statement runs in the transaction and what rollback does.

**C9. Process, tooling, device checks.**
- Examples: S024 BR1-02 (checklist the IT admin cannot do), S025 BR2-01 (backup gate runs after the deploy), S024 BR2-01 (synced skill file would be overwritten).
- Check: For each device or manual check name the person, account, network (plant LAN or not) and device. Delete any check a browser test could do.
- Check: Grep the repo for files marked "synced from" or "generated" before planning an edit. Put release steps in a numbered list and check each can run where it is placed.

**C7. Earlier decision, Plan.MD, stale text.**
- Examples: S001 BR1-01 (goes beyond Plan.MD), S006 BR1-02 (re-asks a decided storage question), S020 BR1-01 (misreads S025), S021 BS1-01 (approved decision missing from brief), S011 BR3-01 (text still states the pre-revision rule), S025 BR3-02 (leftover of an earlier revision).
- Check: Grep `docs/Plan.MD` and the previous two steps' briefs and reports for each noun in your Decisions section. A hit is a citation or a stated departure.
- Check: After each edit for a finding, grep the whole brief for the old phrase and every changed number. Fix every hit before the next round.
- Check: For a brief planned ahead of its turn, list steps committed since its baseline. Grep their reports for migration number, lock note, e2e conventions and new rules.

**C6. Migration and schema.**
- Examples: S012 BR1-02 (event ENUM missed), S011 A1-03 (legacy migration cannot be re-run), S025 BR1-03 (no DB for the upgrade test), S019 BS1-02 and S021 BS1-02 (migration number, S025 conventions).
- Check: For each new value the code writes, grep `local_db.py` for the column, its ENUM and its length. List every column, ENUM and index in one table.
- Check: Read the next free version from `grep "_MIGRATIONS" backend/local_db.py`. State whether `_PRECONDITIONS` applies and name the upgrade-database test.

**C8. DB down and worker contract.**
- Examples: S011 BR1-01 (memberships in `require_auth` break serving with the DB down), S013 BR1-01 and BR2-02, S021 BR1-01 (outcomes cannot be recorded under the worker contract), S025 BR1-01 (`/api/health` must call `ensure_schema`).
- Check: For every new hook, route and worker task write one line: "DB unreachable: it returns ... / skips ...". For a task also write what is stored on success, retry-later and no-retry, and which transaction holds it.

**C11. Standards.**
- Examples: S019 BR1-01 (`expert` is a logistic delay in EN 13306), S013 BR1-04 (control is A.8.2), S017 BR1-07, S015 BR1-07.
- Check: For each standard named, write the clause or table number and one plain sentence of what it says. If you cannot confirm it in `docs/` or an earlier step, write "to verify" instead of a number.

**C12. Size.**
- Example: S002 BR1-04.
- Check: If the draft passes 600 lines, or adds more than one table and two screens, split it before round 1.

## 3. Gaps in the existing self-check (SKILL.md, phase 1)

The ten items already match the major causes. These points are missing or too weak. Proposed text follows each.

1. Item 1 says "verified in the code" but not how; 13 majors were this cause. Replace with:
   > 1. **Every claim about code, a library, a browser or the environment has `file:line` or a run result beside it.** Run a 3-line `uv run python` or `node -e` check for library behaviour (QR version, Pillow, Bootstrap, urllib, `convert("RGB")`). Open the file for "the API shows X". Grep the devops repo, compose and cron jobs for any task the brief says does not exist yet. A claim with no evidence is marked "to verify".

2. Item 2 does not name snapshots or foreign-key locks. Replace with:
   > 2. **Locks**: one numbered lock sequence per route (table, row, mode, including shared locks taken through foreign keys). Compare it with the LOCK ORDER notes in `tickets.py` and `masters.py`. Decide from columns read by the locking statement, never from a plain read made after an earlier plain read (REPEATABLE READ). A counter or "same transaction" rule says what rollback does.

3. Item 3 covers keys, not identity. Add:
   > 3b. **Identity paths**: for each editable field, say whether it changes who can log in or what they see (`active`, login name, role, site). Cover actor = target, normalised names, inactive people, and reused routes that hard-code another key. A request with no identity gets nothing, never admin.

4. Item 4 does not name the recurring files. Replace with:
   > 4. **Tests**: list by file and test name the existing tests the change breaks. Always check `test_role_matrix`, `conftest.py` `_TABLES`, the `db_down` fixture and the `test_migration_*` upgrade tests. For each new test name its fixture and say whether the session DB gives the starting state. Name the e2e specs, targeted or full, and the S024 conventions (allowed 400s, setup by API, shared DB).

5. Item 5 is general; C4 is the largest class. Add:
   > 5b. **State and events**: for every state change write actor x state x already-in-target-state. For every alert or event name the line that writes it and whether that path always runs (a send-back that keeps the intensity writes nothing). Give every input four cells: missing, empty, wrong type, boundary.

6. Item 6 misses staleness inside the brief and since the baseline. Add:
   > 6b. **Self-consistency and staleness**: after every edit, grep the brief for the old phrase and each changed number. For a brief planned ahead of its turn, list steps committed since its baseline and check migration number, lock notes, e2e conventions and new README rules.

7. Item 8 does not cover the worker contract. Append to item 8:
   > ... For a worker task also write what is stored on success, on retry-later and on no-retry, and which transaction holds the claim and the result.

8. No item covers screens (C10, 50 minors). Add:
   > 11. **Screens**: for each dialog or control name the composable and its call contract (what `blank` returns, what `open(seed)` does), which fields can be defaulted, the one-tap path of the common case, the place on the page, and the reason shown for a disabled control on a phone. Say how a destructive control is protected.

9. Item 9 says "checked, not recalled", yet standards still gave 40 minors and nits. Append: "Write the clause number plus one plain sentence; if unverified write 'to verify' instead of a number."

10. No item covers process steps (C9). Add:
    > 12. **Process steps**: grep for "synced from" or "generated" before editing a file. List release or deploy actions in order and check each can run where it is placed. Name the machine, account and network of every manual check.

11. No size gate. Add:
    > 13. If the draft passes 600 lines, or adds more than one table and two screens, split it before round 1.

## 4. Code-review round-1 blockers and majors that trace to the brief

Only 6 round-1 code findings are blocker or major. Three trace to a gap in the brief; the others were the coder's departure or omission.

| Finding | What went wrong | Brief gap? | Brief-level check that would catch it |
|---|---|---|---|
| S018 CR1-01 blocker: every new dialog fails to render | `blank: (seed) => seed` in four dialogs; `useFormModal` calls `blank()` at setup with no argument, so `form` is `undefined` | Yes. The 1231-line brief never states the `useFormModal` contract (only a nit near line 1001 about `blankForm()`) | Screens check (item 11): for each dialog write what `blank` returns and when the seed arrives |
| S021 CR1-01 blocker: push address check bypassed with a backslash | `urlsplit` and `urllib3` (used by `requests`) read the host differently | Partly. The brief named the control (A 8.20, OWASP SSRF) but not "validate with the parser that sends" | Claim check C1 plus: for each URL check, name the library that fetches it and test one hostile input with that parser |
| S026 CR1-01 and CR1-02 blockers: flaky e2e specs | `.or()` locator resolves to two elements; a fill lost during the open animation; `expectDialogFits` skipped | Partly. The brief listed timing facts for the watch (BR1-05) but not for the new specs | Tests check: in the spec list, state each wait as one element, call `expectDialogFits` right after each open, and note that the full run shares state |
| S024 CR1-01 major: S016 cause and action dialogs never opened | Brief § 1.4 listed them; the coder skipped them and did not report | No. Coder omission | Put an acceptance table in the brief with one row per dialog |
| S008 CR1-01 major: unreported departures (row vs cell; page fallback loop) | Brief § 6 was clear | No. Coder departure | None at brief level |

Minor code findings that also trace to a brief gap: S018 CR1-02 (repeat check ignores the earlier ticket's state), S019 CR1-01 and CR1-02 (stale *Schedule* gets 403; a list as `waiting_reason` answers 500: input rules), S025 CR1-02 (lock-order notes miss FK checks, the same cause as S017 BR1-03), S006 CR1-02 (manual check needs a download the page cannot give).

## 5. Which steps get the most findings

Facts from per-step counts (all rounds):
- Most majors: S011 (10, five rounds, 911 lines), S002 (7, three rounds, 887 lines), S006, S021 and S025 (5 each), S024 (4).
- Most minors and nits: S018 (about 38 and 24; 1231 lines, four rounds, one amendment), S021 (about 28 and 25; 1155 lines), S020, S025 and S011.
- Zero majors: S015, S016, S026, S027. These were single-round or tightly scoped briefs that reuse a pattern.
- Round-1 majors per step fell from 1.9 (S001–S014) to 1.3 (S015–S027). Round-1 minors rose from about 6 to about 8 per step. Briefs grew, and findings grew with size.

Patterns (assumption: size and novelty drive the count; the data cannot separate them):
- Lock and RBAC steps get the majors: S002, S011, S012, S017 (locks); S010, S011, S014, S023, S024 (permissions and identity). Amendment rounds on these (S011 r2–r5, S010 r3) found new majors because each revision opened a fresh identity or lock path.
- Steps that bring a new library or outside system get majors from unverified facts: S006 (Pillow, NFS, compose), S014 (segno), S021 (web push), S022 (uv, OSV), S025 (deploy, backups).
- Pure UI steps (S003, S005, S007, S009, S015) get at most one major. Their findings are phone and dialog details (C10) and browser facts (Bootstrap).
- Migration steps get majors only when an ENUM or the legacy data path was missed (S011, S012, S025).
- Big briefs with an amendment (S011, S018, S025) show the stale-text pattern: S011 BR3-01, S018 BR2-03 (a dialog contract that contradicts itself), S025 BR3-02.
- Staleness reviews (10 files) found mostly minors: a migration number (S020, S021), an e2e convention (S019, S020, S021), changed lock notes (S019, S020), and one major (S021 BS1-01, a decision missing from the brief). Item 6b addresses this.
