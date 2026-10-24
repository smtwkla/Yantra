```
Step: S038 — Meters on models and equipment
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035, S036; the S037 brief (Gate A: v29, `meter_types` with the four kinds `counter`, `gauge`, `amount`, `yes_no`, `unit` NULL and `expected_answer` set for `yes_no`) taken as what exists before this step.

Facts file: `scratch/brief-facts-S038.md`, current. The brief is untracked, so there is no git diff of it: I re-read the sections U3 changed (§ 1.5, Out of scope, § 2, the § 4 note, § 5.1, decision 5, § 8, the U3 log entry) and, as the orchestrator asked, every place the brief branches on kind (§ 1.1, § 1.2, § 5.2 `effective_meters`, § 5.5, § 6, `meterLabels.js` in § 3). I did not re-review the rest.

**Verdict: no `blocker` or `major` finding is open.** The U3 changes are in the text and consistent with S037: the freeze names the expected answer, limits are refused for `amount` and `yes_no` with their own messages, and the tests cover both. One `minor` remains: the card and the model view describe every meter as "name, unit, kind, limits", which fits a gauge; the brief does not say what a counter, an amount or a Yes / No meter shows in the unit and limits places. Four nits.

---

## BR3-01 — minor — What a non-gauge meter shows where the brief shows a unit and limits

**Problem.** § 1.1 lists per model meter "its type (name and unit), kind, its limits text"; § 1.2 lists per node meter "name, unit, kind, and for a gauge the limits in force … or 'No limits'"; § 8 tests "`limits_text`'s four wordings". All four wordings are gauge wordings. Three cases are left to the coder:
1. a counter or an amount: does `limits_text` read "No limits" or nothing? "No limits" on a counter reads as a gap to fill, while § 5.1 refuses limits on it ("A counter has no limits");
2. a Yes / No meter has no unit (S037 § 4: `unit` NULL), so "name and unit" shows the question alone. The condition it is checked against is its expected answer (S039 marks *Not OK* against it; S040's row shows the question and two toggles). The card shows a gauge's range (the TPM visual standard, § 2) but not a Yes / No meter's good answer;
3. § 6's `meter_type` object is `{id, name, unit, kind, decimals}` in both GETs: no `expected_answer`, so the card could not show it.

**Why it matters.** The card is the operator's reference for what a good reading is; S039 builds *Log reading* on this card and S040 reads `meter_type` from the same shape. A rule left open here becomes a coder's choice in three steps.

**Options.**
- (a) **Recommended.** Three sentences in § 1.2 (and § 1.1 for the model view): `limits_text` is `null` for a counter and an amount, and the card shows no limits line for them; for a Yes / No meter the card shows "Expected: Yes" / "Expected: No" where a gauge shows its limits, built in `meterLabels.js` from `meter_type.expected_answer` (a label of a stored value, as the kind labels are; the rule itself stays on the type, S037 decision 7); `meter_type` gains `expected_answer` in both GETs of § 6. Tests: a `limits_text` case for a non-gauge (`null`) in `test_meters_core.py`; the yes_no label in `meterLabels.test.js`.
- (b) Let the API's `limits_text` carry the Yes / No wording too ("Expected: Yes"), so the card has one slot from one source. Simpler on the card, but the name `limits_text` then misleads, and the text comes from a frozen type field, not from the limits the function is about.

---

## Nits

- **BR3-02** (nit) § 5.3 *Meter type in use*: say what "change" means — the sent value differs from the stored one, as `_check_code_frozen` does (`masters.py:638`: `"code" in clean and clean["code"] != locked["code"]`), on the row after the merge (S037 § 5.1 merges the body over the stored row). A `PUT` from the edit dialog that re-sends the same kind, unit, decimals and expected answer then passes, and name and active stay editable in practice, not only in the rule.
- **BR3-03** (nit) § 5.1 the three "any limit sent for a …" rows: say that an explicit `null` on a counter, an amount or a Yes / No meter is not "a limit sent" (a form that posts every field stays accepted; only a non-null value is refused), and that this check comes before the number checks, so a counter with `"abc"` reads "A counter has no limits", not "Enter a number …".
- **BR3-04** (nit) § 3 `meterLabels.js` "the kind labels": name the four (*Counter*, *Gauge*, *Amount per period*, *Yes / No*, S037 § 9.1), and say that S037's `MeterTypesPanel.vue` *Kind* column reads them from this file once it exists, so the words live once (S037 is coded first and has no labels file).
- **BR3-05** (nit) § 1.1, § 1.3 the meter type select: show the kind (and the unit when there is one) beside the name in each option, e.g. "Oil temperature (°C, Gauge)", "Oil level above min (Yes / No)", so the dialog's Min / Max fields appearing or not is not the only sign of what was picked.

---

## Checked and found consistent

- **§ 1.5 and decision 5.** The freeze names kind, unit, decimals and the expected answer; the 409 text names the same four; S037 § 1.5 promises exactly this freeze and S037 § 4 has `expected_answer` NULL unless `kind = 'yes_no'`. § 8 tests the freeze of a Yes / No type's expected answer and with an inactive link; name still editable.
- **Out of scope.** "A Yes / No meter's good answer is fixed on its type (S037 decision 7)": S037's decision 7 is *The expected answer on the type*, with the reason given. A counter on a PM interval (phase 4) and an amount as a quantity match S037 § 2 and S039 § 1.2.
- **§ 2.** ISO 4406 is gone; the four bullets stand. The EN 13306 condition-monitoring line covers a Yes / No meter as an observation as much as a gauge (S037 § 2 names it an inspection); nothing more is needed here.
- **§ 4 note.** The limits columns stay NULL for the three non-gauge kinds by a code rule; the CHECK allows NULLs; the kind lives on `meter_types`, so the schema needs no per-kind constraint.
- **§ 5.1.** Three refusal rows, one message each, in the shape of S037's "A Yes / No meter has no unit"; `validate_limits` takes `kind` and `decimals` from the locked type row, so a `yes_no` type's `decimals = 0` never matters (limits are refused before).
- **§ 5.2 `effective_meters`.** It branches on nothing by kind: a non-gauge meter carries NULL limits on both sides, `overridden` is false, "equal to the model" (NULL = NULL) stores no row, and `use_model_limits` on it is a no-op. The six cases of § 8 hold for every kind.
- **§ 5.5.** `meter_limits` can only arise on a gauge (limits refused elsewhere), so the length bound (unit ≤ 20) holds and a NULL unit never reaches `limits_text`. `meter_added` / `meter_removed` carry the name only.
- **§ 8.** `test_models_api.py`: amount and Yes / No with limits → 400 (U3); `test_meters_core.py` covers every § 5.1 row. S039 reads the limits in force from `effective_meters` and adds `last` to the node GET; S040's `meter_type` carries `kind`; nothing in § 6 contradicts them, once `expected_answer` is added (BR3-01).
- **Round-2 acceptances in the text** (re-checked in passing while reading the changed sections): BR2-01 `stored` in § 5.1 and § 8; BR2-02 in § 5.2, § 5.3, § 8; BR2-03 in § 5.3; BR2-04 to BR2-09 each where the Review log says.
