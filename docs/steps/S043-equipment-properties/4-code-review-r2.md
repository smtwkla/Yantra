Step: S043 — Equipment properties: master, classes and models
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 24-10-2026

# S043 — Code review, round 2 (the port to main)

**Verdict: no `blocker` or `major` finding is open.** The port keeps S037 and S038 intact, the renumbering is clean, U8 is built as answered, and CR1-01…CR1-05 are fixed. Every suite is green. There is 1 `minor` finding (a red result missing in the report) and 2 nits.

**What this round covered.** Round 1 was the branch's review, copied over. This round reviews the port in full, because it is new code on a different base:

- the S043 diff: the working tree against the snapshot `refs/steps/S038` (95b400d), plus the untracked files the report names;
- the branch's code, for comparison: `git diff 06e16e4 ffb144c`, and each new file against its `ffb144c` copy;
- the brief's § Port, U8 and the Staleness s1 answers, and the report's section "Port to main (24-10-2026)".

**Files re-read in full:** `properties.py`, `properties_core.py` (`parse_value_keys`, `check_model_values`, `property_view`), `test_migration_v31.py`, `PropertiesPanel.vue`, `ClassPropertiesView.vue`, `ModelPropertiesModal.vue`, `AddPropertiesModal.vue` (script and search input), `e2e/support/properties.js`, the `FormModal.vue` footer. The rest from the hunks, against the branch.

**Not reviewed:** the `.claude/skills/step/SKILL.md` hunk (a `step_snapshot.py` call note) is the orchestrator's, not this step's. The README index row and the brief's Status line are the orchestrator's too.

## Test runs (this review, `YANTRA_TEST_RUN=s043cr2`)

| Suite | Result |
|---|---|
| Backend (pytest, 8 workers) | **2837 passed** (128 s) |
| Frontend (vitest) | **154 passed** |
| Deps tests | **42 passed** |
| Tooling tests | **115 passed** |
| `npx vite build` | built; only the old chunk-size warning |
| e2e, **full** suite, three projects, 6 lanes | **354 passed, 6 skipped, 0 failed** (623 s); the 27 S043 tests (9 per project) all passed, phone-webkit included; the 6 skipped are the existing marked ones |

- **Why the full e2e suite:** the step changes the shared `FormModal.vue` (`closeOnly`) and adds `e2e/support/properties.js` (CLAUDE.md § Browser tests). The full run includes the targeted specs (`masters.spec.js`, `equipment.spec.js`) and `screens.spec.js`.

## Findings

### CR2-01 (minor) — CR1-04's test has no red result

- **Where:** `docs/steps/S043-equipment-properties/3-impl-report.md:73`.
- **Problem:** the answer to CR1-04 says `test_migration_v31.py` checks both texts and that every seed description ends with a full stop. It does not say that the test failed without the fix. CR1-01, CR1-02, CR1-03 and CR1-05 each give their red result; CR1-04 gives none, and no reason.
- **Failure scenario:** a later reader cannot tell whether `assert all(p[3].endswith(".") …)` (`test_migration_v31.py:78`) ever caught the fault. A check that was never seen red could pass for the wrong reason (for example, a `_seed()` that read no descriptions).
- **Fix:** add the red result to the CR1-04 row, e.g. which assertion failed on the branch's seed text. Do not change the code.

## Nits

- **CR2-02** (nit) `backend/tests/test_equipment_api.py:1518`: `class TestProperties:` follows the last line of `TestNoModel` with no blank line, a merge leftover. Add the two blank lines (PEP 8 E302).
- **CR2-03** (nit) `frontend/e2e/masters.spec.js` (test `S043: an option refused on Save …`): the refusal is checked with `toContainText`. Use `expectFieldMessage(dialog, "An option with this label exists")`, as the other refusal tests do, so the S026 rule (the message in view) is checked too.

## Round 1 findings (the branch's review)

| Finding | Status | Checked |
|---|---|---|
| CR1-01 (minor) Enter in the picker's search adds the ticked properties | **Fixed** | `@keydown.enter.prevent` on the search input (`AddPropertiesModal.vue:77`), with a *why* comment. The e2e test presses Enter after one tick and expects the dialog open and the box ticked. Red result given. |
| CR1-02 (minor) a refused option save leaves the list stale | **Fixed** | `saveEdit` (`PropertiesPanel.vue:104-122`) sends options only for a *Choice*. After an option refusal it calls `resetMasters()` and `reload()`, refreshes `editing` (so *Data type* turns fixed once an option was saved), then rethrows, so the message stays under the options. The dirty snapshot is untouched, so *Cancel* still asks. New e2e test; red result given. |
| CR1-03 (minor) a new option row cannot be removed | **Fixed** (the reviewer's option 1) | A ✕ button with `v-else` against the *Active* switch, so only a row with `id === null` has it. After a refused Save, a row whose POST succeeded gets its id and loses the ✕, which is right. The e2e test adds and removes a third row. Red result given. |
| CR1-04 (nit) two seed descriptions lack a full stop | **Fixed** | Both end with a full stop in v31 (`local_db.py`). See CR2-01 for the missing red result. |
| CR1-05 (nit) refusals in key order | **Fixed in code** | `check_model_values` refuses the lowest unknown id first (it has no name), then walks the known properties by name and refuses an inactive or unlinked one in its place. New core test; red result given. |

## Departures declared by the coder (port)

| # | Decision | Judgement |
|---|---|---|
| 1 | CR1-05 fixed in code, not only noted | **Sound.** It makes the code match brief § 5.3 ("checked in the order of the property names"). An unknown id has no name, so "first" is the only order it can have. The screens never send such keys. |
| 2 | CR1-03 as a ✕ button | **Sound.** A silent drop of blank rows would hide a row the user meant to fill. Saved options keep only their *Active* switch, as § 7.1 says. |
| 3 | CR1-02 as a refresh after a partial save | **Sound.** The brief keeps separate option routes (§ 6.1), so one atomic request is out of scope. |
| 4 | Screen texts "Remove option" (tooltip) and "Remove option N" (label) | **Scope B is met:** a verb and the thing it acts on. |
| 5 | `aria-label="Properties"` on the row buttons | **Sound.** It matches S038's *Meters* button. |
| 6 | e2e helper `noModelPart` | **Sound.** It is set up by API (S024), and the part gets its own class. |
| 7 | The operator test makes its own class | **Sound.** No dependence on another test's data. |

## Checked and found consistent

- **S037 and S038 intact:**
  - every untracked S037/S038 file (`meters.py`, `meters_core.py`, the five meter tests, `test_migration_v29.py`, `test_migration_v30.py`, the six meter Vue and JS files, the snapshot tooling) is byte-equal to `refs/steps/S038`;
  - `local_db.py`: v20–v30 unchanged; the only hunk appends v31 after v30, with the "Rollback:" line v27–v30 have;
  - `conftest.py`: S037's `_SEEDED_TABLES` dict kept, with two entries added (`property_definitions`, `property_options` → `migration-v31`); no `_SEED_CREATORS`, no `PROPERTY_SEED_CREATOR` (BS1-02). `_TABLES` still starts with `node_meters, model_meters`; `model_property_values` sits before `equipment_models`, `class_properties` before `equipment_classes`;
  - `equipment.py` LOCK ORDER: S038's meters bullet and the new properties bullet both present; `properties.py`'s docstring has the S038 line (BS1-09);
  - `ModelsPanel.vue`: *Documents*, *Meters*, *Properties*, *Edit*, in that order; `<ModelPropertiesModal>` beside `<ModelMeterFormModal>` (BS1-10);
  - `MastersView.vue`: *Properties* between *Models* and *Meter types* (BS1-10);
  - `EquipmentDetailView.vue`: S036's `ticketRowClass` import and S038's `MetersCard` kept; the card order is *Details*, *Properties*, *Parts*, then *Meters*, as § 7.4 says (BS1-05).
- **Renumbering:**
  - no `S035`, `S036`, `v26` or `migration-v26` left in any S043 file or added line. The one hit is `test_migration_v31.py:7`, which names S031's file on purpose;
  - `test_migration_v31.py` is new, on the v30 pattern (`range(20, 31)` / `range(20, 32)`, `SEED = "migration-v31"`); its upgrade from v30 also keeps a `model_meters` row and `meter_types`;
  - S031's `test_migration_v26.py` has no change against the snapshot.
- **U8, BS1-01 (no model):**
  - `_card_rows` passes `{}` when `model_id` is None, so no query runs `model_id = NULL`;
  - the card hides the "Values from model" line and *Edit model values* when `node.model_id` is null;
  - tests: an API test (`TestProperties::test_a_component_unit_without_a_model…`), a core test, and an e2e test that asserts "—", no model line and no button, as an engineer (who would see the button on a part with a model).
- **U8, BS1-04 (who sees the buttons):**
  - the class row's *Properties* button shows to every reader; the action column now shows to every reader, and its *Edit* button stays for `equipment:edit`;
  - `ClassPropertiesView` hides *Add property…* and *Remove* without `equipment:edit`;
  - the model row's *Properties* button shows only with `equipment:edit`;
  - the operator e2e test asserts all three.
- **`FormModal.vue`:** the `closeOnly` prop defaults to `false`; its footer is a `v-else-if` after `confirming`, so the leave guard still wins; `onSubmit` skips `save` when `closeOnly`. Only `AddPropertiesModal` and `ModelPropertiesModal` pass it. The full e2e run covers the other callers.
- **Migration v31** matches brief § 4.1 and § 4.6 column for column (round 1's list holds). It changes no existing table, so no `_PRECONDITIONS` entry is needed; `test_a_v30_database_with_equipment_keeps_every_row` checks the old tables' rows and columns.
- **Security:** reads use `masters:read`, writes `equipment:edit`; the actor comes from `actor()`; every query uses placeholders, and only constant names and `%s` lists are formatted in. The v31 seed's f-string takes code constants only.
- **Edge cases:** `{}` values (200, no change), keys `"0"` and `"01"` refused by `_ID_KEY_RE`, an unknown model or class (404), the database down (503, `TestDatabaseDown` with the shared `db_down`).
- **The docs pass** (`## Docs updated` against the diff and CLAUDE.md § Docs to keep current):
  - `docs/schema.md`: the four tables in *Built tables* with the ENUM values, the CHECKs, the unique and composite keys; the Mermaid overview has the four tables and six links; the header note names migration v31;
  - `docs/schema.html`: the meta line says v31, 36 tables, 51 links, and the Overview tab has exactly 36 tables and 51 links. The Equipment tab has the four tables with every column and the six links, and its note names them;
  - `docs/Plan.MD`: *Per-class custom fields* gone from *Not in v1*; *Equipment class* names S043 and S044; main's S033 *Fields* line kept;
  - `docs/Maintenance-Philosophy.md`: the glossary row *Property*;
  - `.claude/CLAUDE.md` § SMTW-Review: S043 added for `masters` and `equipment`;
  - no secret, role, real-device check or Keycloak change, so no other doc is due.
- **Manual checks:** the report's `## Manual checks` carries every § 8.4 check as `[auto]` with its test, the two important ones marked. § 8.5 has no real-device check, so `device-checks.md` correctly gains no row.
- **Use on the floor (UX):**
  - all three dialogs use `FormModal` (`modal-dialog-scrollable`), and `expectDialogFits` runs on each;
  - *Remove* on a class needs no confirm, as § 7.2 decides (no value is lost);
  - the screen texts are short and plain, and buttons start with a verb;
  - the card's *Edit model values* is `btn-sm`, like the other card-header buttons on the page; the Masters screens are office screens.
- **Scope:** everything in brief § 1 and § Port is built; S044 is not started; every departure is in *Decisions taken in the port*.

## Manual browser checks for the user

- None from the brief (§ 8.5: none on a real device).
- The full e2e run of this review covers phone-webkit, so the round-1 note about WebKit is closed.
