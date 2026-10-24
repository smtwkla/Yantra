```
Step: S039 — Meter reading entry
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035 (none of its files is named in this brief), plus the S037 (v29) and S038 (v30) briefs as the assumed baseline (neither coded yet). Facts file: `scratch/brief-facts-S039.md` (re-run).

**Verdict: no `blocker` or `major` is open.** The three round 1 majors are in the brief's text (§ 5.3 and decision 6; § 5.1, decision 8 and U2; § 6 and decision 9), not only in the Review log. Four `minor` findings: the lock key of the remove route, a refusal code the sheet (S040) needs from this step's POST, the paging shape, and the e2e set-up on the shared database. Nothing else the sheet needs was lost in the split.

Sections re-read in full: the header, § 1, § 2, § 3, § 5, § 6, § 7, § 8, § 9 and the Review log. § 4 (unchanged) was only checked against the new § 5.2 and § 5.4.

## Findings

### BR2-01 — minor — § 5.3, § 6: the remove route's lock does not say which key it checks, and the obvious one refuses IT admin

**Problem.** `load_node_for_user(cur, id, for_update=True, key=…)` asserts a key and checks it at the node's site (`equipment.py:303–319`, `require_perm_at`). § 5.3 says *Remove* takes (1) "the node row", but names no key. The two keys at hand both fail a case the brief promises:
- `reading:log`: IT admin does not hold it (U2, decision 7), so "remove … by IT admin" (§ 1.4, § 8, BR1-13) gets a 403 at the lock;
- `equipment:edit`: the operator author (§ 1.4, "by its author within 24 hours") gets a 403 at the lock.

**Why it matters.** The coder has to choose, and either choice silently breaks a stated behaviour; the test list would catch one of the two, after the fact.

**Options.**
- (a) **Recommended.** Lock with `key="equipment:read"` (site-scoped, held by everyone who may see the node), then decide *who may remove* from `may_remove(reading, actor, now, can_edit)` with `can_edit = has_perm_at("equipment:edit", node["site_id"])` (`auth_utils.py:389`). The "who" rule is the reading's, so it belongs after the lock, in the core function the brief already has. One line in § 5.3 and the *Key* cell of the DELETE row.
- (b) Lock with `reading:log` and let IT admin fall through a second check. Two paths for one rule.

### BR2-02 — minor — § 5.2.4, § 6: the sheet (S040) has to recognise the "Lower than …" refusal, and this step gives it no way but matching the text

**Problem.** S040 § 1.5 shows the *Meter reset* tick on a row "only after that row was refused with 'Lower than the reading of …'". The POST is this step's. `ApiError` carries `message`, `status` and `field` only (`api_common.py:32–39`); the one `code` the API sends today is the network gate's hand-built JSON (`access_control.py:152`), which `api.js:25` already reads into `err.code`. As written, S040 would have to match the message text, which breaks the day the wording changes (the counter message carries a date and a value, so a regex at that).

**Why it matters.** This is the one thing the sheet needs from this step that the split left out. Adding it later means touching the approved POST.

**Options.**
- (a) **Recommended.** `ApiError` gains an optional `code` (sent as `{error, field, code}`), and the counter-lower 400 of § 5.2.4 carries `code: "counter_lower"`. One line in § 5.2.4 and § 6; `api_common.py` joins § 3 *Where*. S040 then reads `err.code`.
- (b) Leave it to S040 to match the text. Fragile; S040's brief would have to say so.

### BR2-03 — minor — § 6, decision 9: `limit` / `offset` and `{readings, total}` are a second paging shape beside the one in use

**Problem.** The brief cites `tickets.py:623` for `limit` / `offset`. That line is the SQL. The API there takes `page` and `per_page` through `int_arg` (`tickets.py:606–607`; `api_common.py:128–135`: `DEFAULT_PER_PAGE`, `MAX_PER_PAGE`, `MAX_PAGE`, which also keeps the OFFSET inside what MariaDB accepts) and answers `{items, total, page, per_page}`. The equipment list does the same. `limit=30&offset=0` and `{readings: […], total}` would be a parallel pattern with its own bounds checks.

**Why it matters.** Two query shapes for one idea; the coder writes the bounds checking again; the frontend gets a second list shape.

**Options.**
- (a) **Recommended.** `GET /api/equipment/<id>/readings?meter_type_id=&page=1&per_page=30`, answer `{items, total, page, per_page}`, `int_arg` for both. *Show more* asks the next page. Decision 9 ("offset paging", BR1-03 option a) stays true.
- (b) Keep `limit` / `offset` and say why it departs. No reason I can see.

### BR2-04 — minor — § 8 Automated: the e2e set-up on a shared seed node fails on the three projects, and the operator cannot reach the node the existing helper makes

**Problem.** The three Playwright projects share one database (`masters.spec.js:27`, "the three projects share one database") and run in parallel lanes. Judged against that:

1. **`beforeAll` adds Run hours and Oil temperature to "a seed node".** The second project to arrive gets 409 "This machine already has this meter" (S038 § 5.3), so the set-up must accept 201 or 409, or own its node.
2. **Readings on one shared node from three projects collide.** Each test's *Log reading* defaults `taken_at` to now, so two projects in the same minute hit § 5.2.3 ("A reading at this time exists"); the counter test's values interleave across projects (project A saves 100, project B's "good" first reading of 50 is refused as "Lower than"); "the author removes a reading" removes a row another project's test may be reading. The results depend on timing, as S041's bug does (a test touching the shared seed extruder).
3. **The operator's units.** `e2e_operator` holds MCC2 only (`seed_e2e.py:38`); the existing `createEquipment` helper (`equipment.spec.js:238–251`) makes its machines at **SMTW.MCC1**, which the operator cannot see (404). The brief's main test logs "as an operator".
4. **"Another operator"** (§ 8): the seed has one operator with a login. The person who holds `reading:log` at MCC2 and no `equipment:edit` is the supervisor (`e2e_supervisor`, MCC1 and MCC2).

**Why it matters.** Flaky e2e tests cost every later step a re-run, and the brief marks two of these tests **Important**.

**Options.**
- (a) **Recommended.** `readings.spec.js`'s `beforeAll` creates its **own machine per project** at **SMTW.MCC2** (name carrying `testInfo.project.name`, a `createEquipment` variant taking the unit, or the helper moved to `e2e/support/` with a unit argument), adds the two meters to it through S038's API, and every S039 test and `equipment.spec.js`'s "last reading" check use that machine. The reading values and times are then the test's own. "Another operator" becomes the supervisor, named as such ("another holder of `reading:log`").
- (b) Keep the seed node and make every reading's `taken_at` unique per project (an offset of minutes per project) and tolerate the 409 in `beforeAll`. More rules, still shared state.

## Nits

- **BR2-05** (nit) § 6: name the fields of a history row (`id`, `value`, `taken_at`, `is_reset`, `limit_state`, `note`, `created_by`, `created_at`, `can_remove`; `removed_at`, `removed_by` when removed rows are asked for) and the shape of `last` on the meters GET (`{value, taken_at, limit_state}` or `null`). The *Show removed* switch of § 5.4 needs a query flag (`include_removed=1`, `equipment:edit` holders only) that the API table does not list.
- **BR2-06** (nit) § 6: say what the GET does without `meter_type_id`: 400 "Pick a meter" (the history is per meter) is enough.
- **BR2-07** (nit) § 6: the DELETE row says 200; `documents.py:432` answers `"", 204`, and `api.js:44` returns `null` on 204. Use 204, or say why 200.
- **BR2-08** (nit) § 1.3: the empty state. Before any reading, the line reads "No readings yet" and is not a tap target (nothing to show), and the dialog's "Last reading: …" line is left out. Say it.
- **BR2-09** (nit) § 1.3: give the *Low* twin of the saved message ("Saved. Below the limit of 10 °C.") and say what a reading inside the limits does: the dialog closes and the card's last reading updates, no message.
- **BR2-10** (nit) § 1.3, § 5.4: "who" in the history is the login (`created_by`), as the equipment page's *Created by* (`EquipmentDetailView.vue:239`). Say so, so the coder does not join `people`.
- **BR2-11** (nit) § 5.4: `can_remove` on a reset row needs "has an active later reading". Only the newest active reading of the meter has none, so one query for the newest id per GET serves every row of the page, not one query per row.
- **BR2-12** (nit) § 1.4: say the confirm's form: inline in the row, [*Remove*] [*Keep*], as S038's remove (S038 BR1-07). The text is given; the control is not.
- **BR2-13** (nit) § 5.2.4: "a reset not lower than the one before → 400" refuses a replaced meter that reads 0 when the reading before it was 0 (a machine that never ran). Rare; either accept it as the rule or make it "a reset higher than the one before".

## Checked and found consistent

- **BR1-01 in the text.** § 5.3 and decision 6: the node row `FOR UPDATE` as the first statement, every later read plain, no locking range read, the docstring line. `load_node_for_user` runs `LOCK_EQUIPMENT` (`equipment.py:310`) before its plain `_read_node`, so the transaction's snapshot follows the lock grant, the rule `equipment.py:447` already states. The two-connection test of § 8 proves it. The S038 interplay holds: a node meter write and a reading insert both take (1) first; a model meter write takes (4) → (4b) and never (1); the reading insert's FK share lock on `meter_types` waits for a type update to commit and nothing waits the other way.
- **BR1-02 in the text.** § 5.1's row, decision 8, § 1 *Out of scope*, U2. Decision 8 describes S028 correctly: `backdate_days` (`tickets_core.py:108–114`) gives `LONG_BACKDATE_DAYS` to `ticket:backdate` holders (no role: admin only, `config_rbac.py:111`) and to everyone while today ≤ `BACKLOG_UNTIL` (30-11-2026). The departure is stated as the user's choice with its consequence. An own `reading_time_error` and `READING_BACKDATE_DAYS` are right: `too_old_message` asserts the limit is one of the ticket constants and returns the ticket wording, so it cannot say "When was it read?".
- **BR1-03 in the text.** § 6 orders `taken_at DESC, id DESC` and pages by offset; decision 9 names the rejected cursor. Only the parameter shape is at issue (BR2-03).
- **The other round 1 answers in the text.** BR1-04: § 1.4, § 5.2.6, § 5.4, decision 10. BR1-05: § 5.5, with `api.js:20–23` as cited (a failed `response.json()` gives `statusText`; a thrown fetch gives no response at all, which the dialog treats the same). BR1-08: § 2 (§ 7.5.3 for the record, § 7.1.5 explained and pointed to *Calibration*, A.8.15). BR1-09: § 8 set-up (refined by BR2-04). BR1-10: the four names exist at `tickets_core.py:52, 73, 74, 92`, and `tickets_core` imports nothing from a meters module. BR1-11, BR1-12, BR1-13, BR1-16, BR1-18, BR1-19: all present where the log says.
- **The split.** S040 § 5.2 and its "Carried from S039" section take exactly what § 1.5 here lists (the POST with `taken_at`, the DELETE for Undo, `formatReading`, the *Meter reset* help phrase, the failure texts); the sheet read, the nav item, the `localStorage` key, the bottom-bar test and the vitest case are in S040 § 3 and § 8. The refusal code (BR2-02) is the one gap.
- **`reading:log`.** Plan.MD § 3 matrix line 123 (✓ for the five roles, blank for it_admin); `ROLE_INCLUDES` gives the supervisor and the ladder the operator's keys; `SITE_SCOPED`'s comment at `config_rbac.py:158–159` asks for the key; the `test_rbac.py` matrix at `:171–197` must grow for the five roles, as § 3 says.
- **Table v31.** Unchanged since round 1; it carries what § 5.2 and § 5.4 need (`is_reset`, `limit_state`, `removed_at` / `removed_by`, the `(equipment_id, meter_type_id, taken_at)` index for the neighbour reads and the history order).
- **History dialog on a phone.** `FormModal.vue:155` uses `modal-dialog-scrollable`: the 30 rows scroll inside the body and the buttons stay in view.
- **Tests and checks.** The threading pattern is at `test_ticket_work_api.py:805–823`; the device check names account, network and where; the two important e2e checks are browser-judgeable; `equipment.spec.js`'s existing tests are not broken by a new card line.
- **Standards.** EN 13306 condition monitoring, ISO 14224 operating time (the denominator of failure rates), ISO 50001 § 6.6, TPM autonomous maintenance (Plant-Facts line 120 is the notebook), ISO 9001 § 7.5.3 against § 7.1.5, ISO 27001 A.8.15, ISO 55001 § 7.5: apt, correctly placed, and explained in plain terms.
- **Wording (scope B).** The messages of § 5.1 and § 5.2 say what is wrong and what to do; the confirmation names the reading and the consequence; buttons start with a verb.
- **Track and size.** Full track, about 16 files, one migration, one key, locks: right.
