```
Step: S038 — Meters on models and equipment
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035, S036; the S037 brief (Gate A: v29, `meter_types`) taken as what exists before this step.

Facts file: `scratch/brief-facts-S038.md`, re-run on this draft. Every existing file, line and name it lists is where the brief says. The brief is untracked, so there is no git diff of it: I re-read the sections the orchestrator named as changed (the header and U2, § 1.1–1.4, § 2 TPM line, § 3, § 4 the engine line and the delete rule, § 5.1–5.5, § 6, § 8, § 9.1, § 9.2, § 9.5, the Review log) and the code they now rely on. I did not re-review § 5.6, § 5.7 or § 7.

**Verdict: no `blocker` or `major` finding is open.** BR1-01 is fixed: a model's meters open in the panel, as its documents do. Every round-1 answer marked `Accepted` is in the brief's text (checked one by one, below). Three `minor` findings remain: two rules the coder would otherwise decide alone (a partial limits update; an inactive own row of a type the model gained) and one unstated case (meters on an inactive model).

---

## BR2-01 — minor — A partial limits update cannot be checked by the pure `validate_limits` as signed

**Problem.** § 5.1 says an absent `min_value` / `max_value` is "unchanged on update", and `validate_limits(body, kind, decimals, creating)` is pure. A `PUT` that sends only `max_value: 5` against a stored `min_value` of 10 passes the pure check: the function never sees the stored side. The `CHECK` constraint then refuses the write, as a database error, not the 400 "Min must not be above Max" of § 5.1. The same gap is on a first override on a node (no row yet): the brief does not say whether the absent side starts from NULL ("on create") or from the model's limit in force.

**Why it matters.** § 5.3's "an override equal to the model on both sides" needs a defined "after the write" pair, and the coder would pick one of two readings.

**Options.**
- (a) **Recommended.** Give the function the limits in force before the write: `validate_limits(body, kind, decimals, stored)`, with `stored` the row's limits, else the model's (a first override), else NULLs (a create). It merges body over `stored` and checks the pair; the shell stores the merged pair. This is `validate_equipment(body, creating, this_year, stored)`'s shape (`equipment.py:760`). One line in § 5.1 and a test row for each start point.
- (b) Require both fields on every limits `PUT` (the dialog always sends both). Simpler, but § 5.1's "unchanged on update" row then goes, and a client sending one side gets a 400.

---

## BR2-02 — minor — An inactive `own = 1` row of a type the model later gains

**Problem.** § 5.2's last bullet says an `own = 1` row whose type is now on the model is shown as the model's meter "with the node row's limits as its override". It does not say "active". Three cases follow that the brief does not settle:
1. the engineer removed an own meter (`active = 0`, its limits 10–50 still in the row); the model later gains the type with 10–60. The stale 10–50 silently becomes an override;
2. *Set limits* on that model meter: the unique key `(equipment_id, meter_type_id)` forbids a second `own = 0` row, so the write must land in the inactive `own = 1` row. Does it set `active = 1` and so undo the Remove?
3. an override "equal to the model" on an `own = 1` row: § 5.3 says "the `own = 0` row is deleted"; § 4 says an `own = 1` row is never deleted.

**Why it matters.** The one place where `own`, `active` and the delete rule meet; S039 reads the limits in force from `effective_meters`.

**Options.**
- (a) **Recommended.** Three rules in § 5.3, one test each: *Remove* of an own meter sets `active = 0` and both limits NULL (no stale override can appear; readings keep their meaning through the type); a row of a type on the model holds the override whether active or not, and a limits write never changes `active` (a removed own meter stays removed after a later model change); "equal to the model" on an `own = 1` row sets both limits NULL and keeps the row, as *Use the model's limits* does.
- (b) Only active rows count for the override, and *Set limits* on case 2 reactivates the row. Fewer rules, but a Remove is undone by a limits change, and the machine's own meter comes back at the next model change.

---

## BR2-03 — minor — May an inactive model gain or change meters?

**Problem.** § 5.3 "Add a meter to a model" checks the meter type is active and § 5.4 locks "(4) the model row". Nothing says whether the model must be active, or which lock helper the coder uses (`_lock_row`, or `_lock_active_parent` which refuses an inactive one, `masters.py:506`).

**Why it matters.** S012's rule is that an inactive model stays on its equipment (`masters.py:519`). Those machines still run and still need their meters; a refusal would send the engineer to add the same meter on each machine.

**Options.**
- (a) **Recommended.** Allowed: `_lock_row` (404 when missing), no active check; the *Meters* button shows on inactive rows too, as *Documents* does (`ModelsPanel.vue:145`). One sentence in § 5.3.
- (b) Refuse: 409 "This model is inactive. Add the meter on each machine." Consistent with "not newly picked", but it costs the floor more work.

---

## Nits

- **BR2-04** (nit) § 1.1, § 8: the back link in `ModelsPanel.vue` reads "← Models" (line 98), not *Back*. Name it as the code has it, so the meters view, the documents view and the e2e locator agree.
- **BR2-05** (nit) § 1.3: "as the documents' remove" — the documents' inline confirm reads *Yes* / *No* (`DocumentsCards.vue:305`); the brief's *Remove* / *Keep* is the better scope-B wording (a verb that names the result). Say the departure is meant, so the coder does not "align" it back to *Yes* / *No*.
- **BR2-06** (nit) § 5.3 scrapped bullet still cites `documents.py:85` as the home of `SCRAPPED_MESSAGE`; § 3 moves it to `equipment.py` (BR1-16). Make § 5.3 say `equipment.py`.
- **BR2-07** (nit) § 6 node `PUT` body: `active?` → `active: false?`, as the model `PUT` (BR1-18: POST is the one way to reactivate; § 5.3 reactivates an inactive own row on POST).
- **BR2-08** (nit) § 5.1 scope B: on a 0-decimal type the message reads "Enter a number with up to 0 decimals". Say "Enter a whole number" when N is 0.
- **BR2-09** (nit) § 1.3: where *Use the model's limits* sits in `NodeMeterFormModal.vue`. Propose the `#footer-left` slot of `FormModal` (`FormModal.vue:177`, where the masters put `ActiveToggle`), shown only when `overridden`, so it stays apart from *Save*.

---

## Checked and found consistent

- **BR1-01 fixed.** § 1.1 and § 3 put a model's meters in the panel: `metersFor` as `documentsFor` (`ModelsPanel.vue:31`, header comment "Not a dialog, because the cards open dialogs of their own"), one `ModelMeterFormModal` (a `FormModal`) for add and *Set limits*. Every dialog is one form and fits a phone; § 8's important e2e check covers the in-panel view, the dialog fit and the return to the table.
- **Round-1 acceptances in the text.** BR1-02 (§ 5.3, § 5.4: both counts `LOCK IN SHARE MODE`, `_check_code_frozen` at `masters.py:638`); BR1-03 (§ 5.1 `null` row, § 5.3 the equal-override delete, § 6 `overridden`, `limits_text`, `model_limits_text`); BR1-04 (§ 4, § 5.2, § 5.3: `own` never changes; NULLs on an `own = 1` row); BR1-05 (§ 5.1 rows and the signature; `Decimal(str(value))`); BR1-06 (§ 5.5 both sides in force; 125 ≤ 200, `local_db.py:349–350`); BR1-07 (§ 1.3 the two confirmations); BR1-08 (§ 3 `meterLabels.js` kinds and sources only; `limits_text` from the API); BR1-09 (§ 1.2, § 9.1 the alternating pump and the die, Maintenance-Philosophy § 8); BR1-10 (§ 9.5 the cut named, user at gate A); BR1-11 to BR1-23 (each found: `masters_core.py` noted as unchanged with its reason; `tracked_meter_change` described; the card before *Notes*; `ENGINE=InnoDB`; the two `UNIQUE_KEY_ERRORS` entries and their modules; `SCRAPPED_MESSAGE` to `equipment.py` with `documents.py` listed in *Where*; model id from `LOCK_EQUIPMENT`, which returns `model_id` (`equipment.py:176`); POST returns the row, PUT `active: false` only; empty states; "already has"; `equipmentLabels.test.js`; two checks **important**; the TPM visual standard).
- **Lock order (§ 5.4, re-read with the share-lock change).** The type update holds the type row `FOR UPDATE`, then share-locks link rows; every link write takes its type lock before touching a link row, so a link writer that holds a link row already holds the type, and the type update waits on the type, never on a link row: no cycle. Node writes (1) → (4b) → `node_meters`; model writes (4) → (4b) → `model_meters`; no path takes (4b) first. The insert's FK share locks (equipment, meter type) fall on rows the transaction holds.
- **Migration v30.** New tables; the ENUM at `local_db.py:729` is the current one and v30 appends; no `_PRECONDITIONS` entry needed; rollback as stated (`equipmentLabels.js:76` shows an unknown event by its raw name).
- **Scrapped and access.** `load_node_for_user` (`equipment.py:303`): 404 outside the user's units, 403 without the key at the site, no scrapped check — true; the scrapped literal is at `equipment.py:758`, as § 3 says.
- **Blueprint.** `documents_bp` with `url_prefix="/api"` at `app.py:177`, routes spelled out under `/equipment/...`; `meters.py` on the same pattern clashes with nothing.
- **Component-unit without a model** (§ 1.2): v28's CHECK (`local_db.py:762`) allows `model_id` NULL only at that level, so "none for a component-unit without a model" is the only model-less case.
- **Standards.** ISO 14224 clause 8 (equipment data: what holds for every unit of a model versus unit data), EN 13306 condition monitoring, ISO 55001 § 7.5 (information: a limit change with who and when) and the TPM visual standard line are apt and correctly placed; the numbers stay "to verify".
- **Manual checks.** Five automated checks, two **important**, all judgeable by a browser; the device list is empty, which is right.
- **Tests.** `conftest._TABLES` cleans with `FOREIGN_KEY_CHECKS = 0` (`conftest.py:180`), `meter_types` in `_SEEDED_TABLES` (S037); `test_models_api.py` exists; `test_meter_types_api.py` is S037's.
