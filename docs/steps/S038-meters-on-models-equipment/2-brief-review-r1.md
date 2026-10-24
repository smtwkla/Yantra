```
Step: S038 — Meters on models and equipment
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035; the S037 brief (v29, `meter_types`) taken as the baseline for what exists before this step.

Facts file: `scratch/brief-facts-S038.md` (current). Every file, line and name the brief cites that exists today was found where the brief says (`load_node_for_user` at `equipment.py:303`, `_write_events` at `:421`, `SCRAPPED_MESSAGE` at `documents.py:85`, the v25 ENUM at `local_db.py:729`, `describeEvent`'s default at `equipmentLabels.js:76`, the tickets error line at `EquipmentDetailView.vue:197`, the Details / Parts row at lines 220–247, `documents_bp` registered with `url_prefix="/api"` at `app.py:177`).

**Verdict: one `major` finding is open (BR1-01, the model meters dialog). No blocker.** The data model, the lock order and the API are sound; the findings below are about one screen's shape, a lock-read detail, missing rules the coder would otherwise decide, and wording.

---

## BR1-01 — major — The model's *Meters* dialog lists, adds, edits and removes in one dialog

**Problem.** § 1.1 and § 3 put a model's meters in a dialog, `ModelMetersModal.vue`, that "adds a meter, edits the limits, and removes a meter". A list with a per-row *Set limits* needs a second form for the limits. Either that form is a second dialog on top of the first, or the rows carry inline inputs and one Save, which needs a batch API that § 6 does not have. The dialog also grows with the list.

**Why it matters.** No screen in Yantra opens a dialog from inside a dialog (`FormModal.vue` is one Bootstrap modal around one form; the "Discard your changes?" bar is inline). `ModelsPanel.vue` already met this exact case with documents and chose the in-panel view: "Not a dialog, because the cards open dialogs of their own" (its header comment; the `documentsFor` state and the *Back* button). The brief departs from that pattern without stating it, and the coder would have to invent stacked modals or a batch save. The user approves the shape of a screen; this one is not settled.

**Options.**
- (a) **Recommended.** Reuse the in-panel view of `ModelsPanel.vue`: the row's *Meters* button sets `metersFor = m`, the table is replaced by the model's meters list (name, unit, kind, limits text, *Set limits*, *Remove*), with *Add meter* above it and *Back* in the header, as `documentsFor` does. Add and *Set limits* open one `FormModal` (meter type select on add; Min and Max; the same `ModelMeterFormModal` for both). Nothing new to design; every dialog stays one form and fits a phone.
- (b) Keep one dialog with inline inputs per row and one Save; add a batch endpoint. More API, more code, and a dialog that grows with the list.

---

## BR1-02 — minor — The in-use count under the meter type lock should be a locking read

**Problem.** § 5.4 "Meter type update": "the meter type row alone, then the plain counts", with the argument that a concurrent link insert takes its own `FOR UPDATE` of the type first, so it waits, and "the count cannot miss it".

**Why it matters.** The argument holds only while the count is the transaction's first consistent read. Under REPEATABLE READ the snapshot is fixed at the first plain `SELECT`; if any plain read precedes the lock wait (a `fetch_one` of stored values, as `update_equipment_model` does at `masters.py:525`), a link committed during the wait is invisible to the plain count, and the freeze (§ 1.5) is bypassed: a unit change would re-label every past reading (S039). The code already has the pattern for exactly this: `_check_code_frozen` (`masters.py:638`) counts `LOCK IN SHARE MODE` and its docstring gives this reason.

**Options.**
- (a) **Recommended.** Count both tables `LOCK IN SHARE MODE` (as `_check_code_frozen`), and say so in § 5.4. Lock order unchanged: the type row is held; the share locks fall on link rows, which only the link writes touch, after their own type lock.
- (b) Keep the plain count and add a rule "no plain read before `_lock_row` in the meter type update". Fragile; a later edit breaks it silently.

---

## BR1-03 — minor — `null` on a limit, and how the API says an override exists

**Problem.** § 5.1 says an absent `min_value` / `max_value` is "unchanged on update". It does not say what an explicit `null` does. The *Set limits* dialog needs it: the engineer empties *Min* and keeps *Max*. § 6's node GET returns `min_value, max_value, model_min, model_max` and no flag; an override equal to the model's limits (10–60 set on a node whose model says 10–60) is then indistinguishable from "no override", though a row exists and § 4 says a row means "a limit differs".

**Why it matters.** Two rules the coder would decide alone, and the card cannot know when to show *Use the model's limits*.

**Options.**
- (a) **Recommended.** Add to § 5.1: `null` clears that limit (stored NULL); `use_model_limits: true` clears both and follows § 4's delete rule. Add to § 6 node GET: `overridden: bool` (an active `own = 0` row exists). Add to § 5.3: an override whose two limits equal the model's is refused with 400 "These are the model's limits. Use *Use the model's limits* instead." (`max_value`) — or accepted and stored; pick one. Refusing keeps § 4's rule "an override exists means a limit differs" true in the data.
- (b) Accept equal overrides and drop the sentence in § 4. Simpler; the card then relies on `overridden`.

---

## BR1-04 — minor — An own meter the model later gains: what *Use the model's limits* and a model change do to its row

**Problem.** § 5.2 last bullet: an `own = 1` row whose type is now also on the model is "shown once, as the model's, with the node row's limits as its override". § 4 says an override with both limits NULL is deleted. The brief does not say whether *Use the model's limits* on such a meter deletes the `own = 1` row (then the node loses its own meter when the model later drops the type) or sets both limits NULL and keeps it. It also does not say whether the row's `own` flag flips.

**Why it matters.** This is the one case where the `own` flag and the delete rule meet; S039's readings are keyed on (node, type) and survive either way, but the node's meter list after a model change depends on the answer.

**Options.**
- (a) **Recommended.** Rule: `own` never changes after insert. *Use the model's limits* on an `own = 1` row sets both limits NULL and keeps the row; on an `own = 0` row deletes it. A model change then gives back the own meter with no limits. One sentence in § 5.3 and a case in `test_meters_core.py` / `test_meters_api.py`.
- (b) Delete the row in both cases. Simpler, but the machine's own meter silently disappears.

---

## BR1-05 — minor — § 5.1 row 3 contradicts the "numbers as strings" row

**Problem.** Row 3: "a limit not a number (string, bool) …" → 400. Last row: numbers are "sent and returned as strings ("62.5")". A coder reading row 3 refuses every string, which refuses every valid request.

**Why it matters.** The two rows cannot both be followed.

**Options.**
- (a) **Recommended.** Row 3: "a limit that is a bool, a float, or a string that is not a decimal number". Last row: "accepted as a decimal string or an integer; parsed with `Decimal(str(value))`, never `float`; returned as strings". Give `validate_limits` its signature: `validate_limits(body, kind, decimals, creating)`, pure, called after the type's locked read supplies `kind` and `decimals`.
- (b) Accept JSON numbers too, parsed through `str()`. Fine for 3 decimals; say so if chosen.

---

## BR1-06 — minor — The `meter_limits` history text is not fully specified

**Problem.** § 5.5: old "Oil temperature: 10–60 °C", new "Oil temperature: up to 55 °C", and "the model's limits read as "model limits" when an override is set or cleared". The last clause has two readings: the side with no override shows the model's values ("10–60 °C"), or it shows the literal words "model limits". § 1.4's example shows values on both sides.

**Why it matters.** This is text the user reads in the history (scope B), and the coder would pick one.

**Options.**
- (a) **Recommended.** Both sides always show the limits in force, from `limits_text`: setting an override writes old = the model's values, new = the override; clearing it writes the reverse. Drop the "model limits" clause. `describeEvent` then reads "Meter limits: Oil temperature: 10–60 °C → up to 55 °C". Each side is at most 60 (name) + 2 + 2 × 18 (numbers) + 3 + 20 (unit) ≈ 125 characters; the columns are `VARCHAR(200)` (`local_db.py:350`), so say that the texts fit.
- (b) Mark the model's side "(model)": "Oil temperature: 10–60 °C (model)". More to read; only if the user wants the source in history.

---

## BR1-07 — minor — *Remove* has no confirm step

**Problem.** § 1.1 removes a meter from a model and § 1.3 removes an own meter from a node on one tap. Removing a model meter takes the meter off every machine of the model at once (decision 1) and off S039's reading sheet for all of them.

**Why it matters.** A significant action never on a single tap (the review checklist; `DocumentsCards.vue` and `ActiveToggle.vue` already confirm inline before removing or deactivating).

**Options.**
- (a) **Recommended.** Inline confirm as the documents' remove: *Remove* → the row shows "Remove Oil temperature from Atlas Copco GA37? Every machine of this model loses it. Readings stay in history. [Remove] [Keep]". On a node: "Remove Oil temperature from this machine? Readings stay in history." Name the words in § 9.2.
- (b) No confirm, since Add reactivates the row. The engineer still has to know the meter was removed and from where.

---

## BR1-08 — minor — The limits wording is written twice, backend and frontend

**Problem.** § 3 adds `meterLabels.limitsText` with "the same four wordings as `meters_core.limits_text`". The backend writes the words into history; the frontend recomputes them for the card.

**Why it matters.** A business wording duplicated in the frontend (audit 21-10-2026 [13], queued tidy-up). The two drift the first time one changes.

**Options.**
- (a) **Recommended.** The node GET and the model GET return `limits_text` per meter (and `model_limits_text` on a node meter), from `meters_core.limits_text`. `meterLabels.js` keeps only the kind labels and the source words ("From the model", "This machine only"); `meterLabels.test.js` shrinks to those.
- (b) Keep both and a test that pins the four strings on each side. More tests for less.

---

## BR1-09 — minor — The example behind open question 1 is wrong

**Problem.** § 1.2 and § 9.1: "an extruder's gearbox (a component-unit) has its own run hours (Plant-Facts line 117)". Line 117 says the gearbox oil is changed every 5,000 run hours; those are the extruder's hours. `Maintenance-Philosophy.md` § 8 says so explicitly: "a plan names one meter, its own node's or an ancestor's — a gearbox on the extruder's hours, an alternating pump on its own. No inheritance logic (ISO 14224: hours at the level where they differ)."

**Why it matters.** The user decides § 9.1 (all levels may carry meters) on this fact. The decision is still right, for other reasons.

**Options.**
- (a) **Recommended.** Replace the example with the two the philosophy gives: an alternating pump (a component-unit) with its own hour meter; a die (a component with a serial, § 8 *Tooling*) whose strokes per press follow from readings. Keep the assumption.
- (b) Limit meters to the equipment level. Rejected by the philosophy's own examples.

---

## BR1-10 — minor — Size: two concerns in one step; the brief should name the cut

**Problem.** The facts file counts 25 files (22 code and tests, 3 docs). The step holds two concerns that could ship apart: a model's meters in Masters, and a node's meters on the equipment page with history. `.claude/skills/step/SKILL.md` (Size, 22-10-2026) says the planner proposes a split in one line in that case; § 9.5 only says "to check".

**Why it matters.** A judgement for the user, not the planner (README § Step ID: one reviewable slice).

**Options.**
- (a) **Recommended.** Keep one step, and say why in § 9.5: the migration (both tables), `meters_core.effective_meters` and the freeze are shared, and the card is empty without model meters; the model part is about 8 files. The user decides.
- (b) Split: S038a model meters, the freeze and v30 (both tables, so S038b has no migration); S038b the node routes, the card, history. Two gates for a smaller review each.

---

## Nits

- **BR1-11** (nit) § 3 Backend: `masters_core.py` is listed as "unchanged". Drop it from *Where*, or say the one reason it is listed.
- **BR1-12** (nit) § 3: `tracked_meter_change` is named and never described. Say what it returns (the `(event, old, new)` tuples for `_write_events`), or drop it.
- **BR1-13** (nit) § 3 Frontend: "after *Details* / *Parts* …, before the documents" — *Notes* and *History* sit between. Say "after the Details / Parts row, before Notes" (or after History).
- **BR1-14** (nit) § 4: the two `CREATE TABLE`s lack `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`, which every table has.
- **BR1-15** (nit) § 5.3: name the `UNIQUE_KEY_ERRORS` entries (`uq_model_meters` → `meter_type_id`, "…"; `uq_node_meters` likewise) and the module each is registered in, as `masters.py:48` does.
- **BR1-16** (nit) § 5.3: `meters.py` importing `SCRAPPED_MESSAGE` from `documents.py` makes a meters module depend on the documents module for an equipment rule; the same literal is at `equipment.py:758`. Put the constant in `equipment.py` (import it in `documents.py`, one line) and list that change in *Where*.
- **BR1-17** (nit) § 5.2: say that the model id `effective_meters` uses on a write comes from the locked node row (`LOCK_EQUIPMENT` returns `model_id`), not the plain re-read.
- **BR1-18** (nit) § 6: POST model meter says "201" with no body; say "201, the row" (or the list, as the node POST). PUT `model-meters` `active?` and POST's reactivation are two ways to reactivate a row: keep one (POST reactivates with the sent limits; PUT `active: false` only).
- **BR1-19** (nit) § 1.2 / § 1.3 empty states: the card with no meters ("No meters." and *Add meter* for editors); the *Add meter* picker when every active type is already on the node or model ("Every meter type is on this machine already. Add meter types in Masters › Meter types.").
- **BR1-20** (nit) § 5.3 scope B: "This model has this meter" → "This model already has this meter"; "This machine has this meter" → "This machine already has this meter".
- **BR1-21** (nit) § 3 Tests: `frontend/tests/equipmentLabels.test.js` gains the three events (`describeEvent`); it is not listed.
- **BR1-22** (nit) § 8: no check is marked **important**. Mark the two that carry the acceptance (the model add with limits; the node override with its history line).
- **BR1-23** (nit) § 2: one line for the owner on TPM autonomous maintenance: the limits shown on the machine's card are its *visual standard*, the range the operator checks the gauge against; S039 makes the check a reading.

---

## Checked and found consistent

- **Lock order.** Node writes: (1) node `FOR UPDATE` through `load_node_for_user(key="equipment:edit")` → (4b) meter type → the `node_meters` row; the insert's FK share locks fall on rows this transaction already holds. Model writes: (4) model → (4b) type → `model_meters`. Equipment writes: (1) → (4) → (5). No path takes (4b) then (1), (4) or (5); `documents.py` and `tickets.py` take no meter lock. The two docstring additions (equipment.py (4b) after (4); masters.py model → meter type) describe it correctly. The plain read of the model's meters on a node write (decision 6) is a display race only, as stated.
- **Scrapped and access.** `load_node_for_user` has no scrapped check (true); the brief decides scrapped from the locked row, as `documents._lock_node_for_change` does. Route-level `require_perm("equipment:edit")` plus the site check inside `load_node_for_user` is the `equipment.py` pattern. `equipment:edit` → engineer, manager (ladder), IT admin (`config_rbac.py:96`), as S012 and S037 use it for models and meter types; the model routes check it on the union, as `masters.py:500`.
- **Migration v30.** New tables and an ENUM widened at its end: no `_PRECONDITIONS` entry needed; `MODIFY` is re-runnable; the v25 statement at `local_db.py:729` is the current ENUM. `test_migration_v30.py` follows the `test_migration_v28.py` shape. `conftest._TABLES` cleans with `FOREIGN_KEY_CHECKS = 0`, so the two names can join it anywhere; placing them first is still right.
- **S037 baseline.** `meter_types` columns (`kind`, `decimals`, `active`), `MAX_DECIMALS = 3`, `DECIMAL(14,3)`, the freeze promised in S037 § 1.5 / § 5.3 and the "deactivated type stays where linked" rule match S037's brief.
- **S039 forward.** S039 keys readings on (node, meter type), calls `effective_meters` for "in force", reuses `meters_core.py`, `meters.py`, `MetersCard.vue` and `meterLabels.js`, and expects the node GET to gain `last`. All consistent with this brief.
- **Existing tests.** `describeEvent`'s default case keeps `equipmentLabels.test.js` green; `test_equipment_api.py` compares event lists per node, which gain nothing here; `test_rbac.py` unchanged (no new key).
- **Rollback.** The previous release ignores both tables and shows an unknown event by its raw name (`equipmentLabels.js:76`): true.
- **Standards.** ISO 14224 (equipment data: what holds for every unit of a model versus what is unit data) and EN 13306 (condition-based maintenance: measure, compare with a limit, act) are the right two; ISO 55001 § 7.5 for the traceable limit change and ISO 4406 for the per-press target are apt. Clause and term numbers are flagged "to verify", as the user's copies must settle them.
- **Manual checks.** The automated list is what a browser can judge (dialog fits, card shows, history line); the device list is empty, which is right for this step.
