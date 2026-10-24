```
Step: S039 — Meter reading entry
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035, S036 (their edits to `EquipmentDetailView.vue` and `equipment.spec.js` are small; the lines the brief cites, `:197` and `:239`, still hold), plus the S037 (v29) and S038 (v30) briefs as the assumed baseline (neither coded yet). Facts file: `scratch/brief-facts-S039.md`.

**Verdict: no `blocker` or `major` is open.** The U3 changes hold: the remove lock with `equipment:edit` is sound, the `limit_state` ENUM fits every kind, and the counter rules stay off amounts. Four `minor` findings: the 403 text the brief promises is not the one the lock helper gives; the Yes / No dialog's footer and the place of its two buttons are unsaid; the e2e set-up machine's model is the one S038's own example puts *Oil temperature* on; the Yes / No path has no API test and no named owner of the word ↔ 1/0 mapping.

Sections re-read: § 1.1–1.5, § 2, § 3, § 4, § 5.1, § 5.2, § 5.3, § 6, decisions 4 and 11, § 8, Acceptance, § 9.5, § 9.8, § 9.9, and the Review log (U3, round 2). The rest was not re-reviewed.

## Findings

### BR3-01 — minor — § 5.2.6, § 5.3: the 403 "Only an engineer can remove a reading" cannot come from the lock the brief names

**Problem.** § 5.3 puts the key check in `load_node_for_user(…, for_update=True, key="equipment:edit")`. That helper calls `require_perm_at` (`equipment.py:317–318`), which raises its own text: "You can't do this at SMTW" (`auth_utils.py:413`). It has no message parameter. § 5.2.6 promises a different text.

**Why it matters.** The coder has to choose: change the shared helper, add a second check before the lock, or let the test for the text fail. Every other site-scoped write answers with `require_perm_at`'s text.

**Options.**
- (a) **Recommended.** § 5.2.6 says the 403 is `require_perm_at`'s, "You can't do this at <site>", as every site-scoped write. Nobody sees it in the normal flow: *Remove* is hidden where `can_remove` is false. Drop "Only an engineer can remove a reading".
- (b) Keep the text and check `has_perm_at("equipment:edit", site)` in the route before the lock. A second path for one rule.

### BR3-02 — minor — § 1.3, decision 11: the Yes / No dialog keeps a *Save* button it does not use, and a note typed after the tap is lost

**Problem.** `ReadingFormModal.vue` is a `FormModal`: its footer always shows *Cancel* and *Save* (`FormModal.vue:176–186`; `saveDisabledReason` greys *Save*, nothing hides it). § 1.3 puts the two buttons "in place of *Value*", at the top of the body, above *Time taken* and *Note*, and says one tap saves. Three things follow that the brief does not say:
1. what *Save* in the footer does on a Yes / No meter (a submit with no answer);
2. the order on the screen: the tap is the save, so *Time taken* and *Note* must be set before it, but they sit below the buttons. An operator who taps *No* and then wants to write "topped up" has no way: the dialog closes, and the operator cannot remove or edit (U3);
3. a mis-tap on one of two large buttons saves at once, and only an engineer can take it back. Decision 11 does not name this consequence.

**Why it matters.** The one-tap entry is the point of decision 11. Where the buttons sit and what the footer shows decide whether it works on the floor.

**Options.**
- (a) **Recommended.** The body order is *Time taken*, *Note*, then the Yes / No pair as the last block, so what the user sees above is what the tap saves. `FormModal` gains a boolean prop `withSave` (default `true`) that leaves only *Cancel* in the footer; `FormModal.vue` joins § 3 *Where*, and the full e2e suite runs (shared code, CLAUDE.md § Browser tests). Decision 11 adds: a wrong tap stays until an engineer removes it; the next reading shows the true state.
- (b) The sheet's shape (S040 § 1.4): two toggles and *Save*. Two taps; decision 11 rejected it.
- (c) Keep the buttons at the top and `saveDisabledReason` on *Save*. A greyed button the user cannot use, and point 2 stays.

### BR3-03 — minor — § 8 Automated: the set-up machine is an Atlas Copco GA37, the model S038's own example gives *Oil temperature* to

**Problem.** `createEquipment` (`equipment.spec.js:238–251`) makes its machines on the model "Atlas Copco GA37". S038's brief uses GA37 for its model example ("Remove Oil temperature from Atlas Copco GA37? Every machine of this model loses it.", S038 § 1.3) and its e2e test "engineer adds Oil temperature with limits to a model" names no model. If that test picks GA37, as the example suggests, then in the lane where it runs before `readings.spec.js`'s `beforeAll`, the set-up's own-meter POST of *Oil temperature* gets 409 "This machine already has this meter" (S038 § 5.3), and the machine's limit is the model's, not the "up to 60 °C" the *High* test expects. The order of spec files in a lane is not fixed, so the result depends on timing, as S041's bug did.

**Why it matters.** Two of this step's e2e tests are **Important**, and a flaky set-up fails all of them.

**Options.**
- (a) **Recommended.** The moved `createEquipment` takes the model too: `createEquipment(name, unit, model)`. `readings.spec.js` makes its machine on `SMTW-HYP-01` (the hydraulic press model, `seed_dev.MODELS`), which no e2e test gives meters to; § 8 says so. One line in S038 § 8 asks its e2e tests to keep off that model.
- (b) The set-up accepts 409 on a meter the model already carries and sets the 60 °C by S038's override PUT. More rules, and the test still depends on another step's choices.

### BR3-04 — minor — § 3, § 8: the Yes / No path has no API test, and no function owns the word ↔ 1/0 mapping

**Problem.** § 4 says the row stores 1 / 0 and the API reads and writes `"yes"` / `"no"`, never the numbers. § 3 names no function for either direction, so the coder puts the mapping where it falls (the route, the row builder, `validate_reading`, or two of them). `test_readings_api.py` (§ 8) has no Yes / No case: the only test of the path is the e2e "a No … shows Not OK", in the browser.

**Why it matters.** The mapping is a rule of this step; the backend suite is where rules are proved. A later channel (S040's sheet, the `pm` source) relies on the same words.

**Options.**
- (a) **Recommended.** § 3 names the two places: `validate_reading` returns `Decimal(1)` / `Decimal(0)` for a Yes / No meter's `"yes"` / `"no"` (pure, with `answer_state` beside it), and one row builder in `meters.py` turns the stored value back into the word for the history GET, the POST's answer and `last`. § 8 adds to `test_readings_api.py`: `"no"` on an expected-*Yes* type → 201, `value: "no"`, `limit_state: "not_ok"`; `"yes"` → `limit_state: null`; `is_reset` on it → 400; `"1"` → 400 "Pick Yes or No"; the history and `last` carry the word.
- (b) Leave it to the coder and the code review. Two rounds later than needed.

## Nits

- **BR3-05** (nit) § 3: `validate_reading(value, decimals, reset, note)` has no `kind`, but four rows of § 5.1 depend on it (a counter below 0, an amount below 0, a Yes / No value, `is_reset` off a counter). Give it the kind, and say that for a Yes / No meter the value rule is "Pick Yes or No" alone: the number rows do not apply to it.
- **BR3-06** (nit) § 1.3 *History*, § 1.4: the history row's badges read "*High* / *Low* / *Reset*"; add *Not OK*. The remove confirmation's bracket reads "(No)" for a Yes / No reading and "(420 pcs)" for an amount, through `formatReading`.
- **BR3-07** (nit) § 1.3: *Yes* and *No* do not start with a verb (scope B). State the departure, as S038 did for *Remove* / *Keep* (S038 BR2-05): the heading is the question, the buttons are its answers.
- **BR3-08** (nit) § 2: one line for the Yes / No kind, as S037 § 2 has it: EN 13306 calls a check for conformity by observation an *inspection*; this step records the inspection's result, and *Not OK* is its nonconformity.
- **BR3-09** (nit) § 5.2.6: say whether a reading on a scrapped node can be removed. Recommended: 409 `SCRAPPED_MESSAGE`, decided from the locked row, as every other write on a scrapped node.
- **BR3-10** (nit) Acceptance: add the Yes / No case: "a *No* on *Oil level above min* saves with one tap and shows *Not OK*".

## Checked and found consistent

- **The lock order with `equipment:edit`.** The key is in `SITE_SCOPED` (`config_rbac.py:162`) and held by `maint_engineer` and `it_admin` (`:96`); the manager inherits it (`ROLE_INCLUDES`). A token role holds it at every site (`has_perm_at`, `auth_utils.py:396`), and IT admin reaches every unit (`equipment:read_all_units`, `equipment.py:290–295`), so "remove by IT admin" passes the lock. The order (1) node row → the reading row `FOR UPDATE` → the later-reading check, plain → update holds: the log path also takes (1) first, so a later insert waits on the node and the plain check sees every committed later reading. No path takes a reading row and then a node; S038's model writes never take (1). No cycle.
- **`limit_state` against every kind.** Gauge: `low` / `high` / NULL from the limits in force; counter: NULL; amount: NULL; Yes / No: `not_ok` / NULL from the type's expected answer. § 1.2, § 4, § 5.2.5 and decision 4 agree. Storing it at save is right for Yes / No too: S038 § 1.5 freezes the expected answer once the type is used, so no later change can disagree with a stored state.
- **Counter rules kept off amounts.** The order check is "counters only" (§ 5.2.4); `is_reset` on an amount is 400 (§ 5.1); an amount has no limits (S038 *Out of scope*) and stores NULL (§ 5.2.5); "below zero" has its own message; § 8 tests the lower-than-before 201, the reset 400 and the NULL state. The same-minute rule (§ 5.2.3) applies to every kind, which is right.
- **The Yes / No type's shape (S037).** `expected_answer` on the type, no unit, decimals 0, frozen once used (S038 § 1.5). The API words `"yes"` / `"no"` match S037's ENUM. `Decimal("yes")` can never pass the number rows, so the kind must pick the rule (BR3-05).
- **The e2e set-up.** `POST /api/masters/meter-types` needs `equipment:edit` (S037 § 6), which `e2e_engineer` holds at SMTW with every unit (`seed_e2e.py:42`); the S038 node POST at SMTW.MCC2 by the same engineer; `e2e_operator` holds MCC2 (`:38`); `beforeAll` receives `testInfo`, so `testInfo.project.name` is available; the type's name per project keeps S037's unique key happy across the three projects of one lane. `createEquipment` is as the brief says (admin, SMTW.MCC1, GA37; `equipment.spec.js:238–251`).
- **S040 after U3.** The sheet shows *Undo* to `equipment:edit` holders only and tells others "Saved. Ask an engineer to remove it if it is wrong." (S040 § 1.4, decision 2); its Yes / No row is two toggles plus *Save readings* (S040 § 1.4), with the same words "Saved. Not OK: the expected answer is Yes."; the *Meter reset* tick keys on `code: "counter_lower"`. Nothing the sheet takes from this step changed shape.
- **Round 2 answers in the text.** BR2-01: superseded by U3, § 5.3 and § 6 name `equipment:edit`. BR2-02: `code: "counter_lower"` in § 1.5, § 5.2.4, § 8; `api_common.py` in § 3. BR2-03: `page` / `per_page`, `{items, total, page, per_page}`, § 6, decision 9. BR2-04: the own machine per project, § 8. BR2-05…BR2-13: the row fields and `last` (§ 6), "Pick a meter" (§ 6), 204 (§ 6), "No readings yet" (§ 1.3), the *Low* message and the silent close (§ 1.3), the login as "who" (§ 1.3), one query for `can_remove` (§ 5.4), the inline [*Remove*] [*Keep*] (§ 1.4), a reset **higher** than the one before (§ 5.2.4).
- **Cited code.** `ApiError(message, status, field)` and `{error, field?}` at `api_common.py:32–46`; `EventFields.vue` has `withRemark` and `timeLabel`; `EquipmentDetailView.vue:197` is the tickets card's load failure and `:239` shows `created_by`; `tickets_core.py:52–92` as the facts file lists.
- **Tests for U3.** Remove by engineer, manager and IT admin; 403 for the operator who logged it and for the supervisor; the Yes / No core cases (`answer_state`, `"maybe"` / `1` / `true` refused); the amount cases. The device check names account, network and where; the Yes / No e2e test is browser-judgeable (height and viewport) and rightly **Important**.
- **Standards.** ISO 22400-2 (U3) is the right home for an amount: its KPIs (availability, throughput rate, quality ratio) are built from base elements such as *produced quantity* and *good quantity* per time unit; a shift's production is that element. The rest of § 2 is unchanged since round 2.
- **Wording (scope B), U3 texts.** "Pick Yes or No", "An amount cannot be below zero", "Only a counter can be reset", "The amount for the period just ended, such as this shift." and "Saved. Not OK: the expected answer is Yes." are one line each, say what is wrong or what happened, and name no field. The one text that fails is BR3-01's, which the lock never sends.
