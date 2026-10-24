Step: S035 — Equipment properties: master, classes and models
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 24-10-2026

Reviewed against: 437d993 (the working tree is clean: the revised brief and `2-brief-review-r1.md` are in that commit; the commit `89c3e2b` named in the request does not exist)

**Verdict: no `blocker` or `major` finding is open.** Round 2, full track. Every round-1
finding marked `Accepted` is in the brief's text (checked one by one below). Four `minor`
findings: three are wiring details the BR1-03 and BR1-04 changes now leave to the coder (a
flag the GET does not carry, which permission computed the card button follows, the dirty
guard against an async load), and one leftover line in § 8.2 that contradicts § 3.2. Facts
file read: `scratch/brief-facts-S035.md` (refreshed this round).

**Sections re-read** (the diff `88b7df2..437d993` of the brief, plus what the changes touch):
header; § 1 items 2, 4, 5 and *Type or property*; § 2 bullets 1–3; § 3.2, § 3.3
(`EquipmentDetailView` row); § 4.6; § 5.1–§ 5.4; § 6.1, § 6.2; § 7.1–§ 7.4; § 8.2–§ 8.4;
§ 9.1, § 9.2; § 10 decisions 8–9; § 11; Review log. Code read for them: `useFormModal.js`,
`useMasterForm.js`, `api_common.py`, `masters.py` lines 45–69, `conftest.py` lines 139–170,
`test_access_control_api.py`, `test_auth.py`, `test_health.py`, `EquipmentDetailView.vue`,
`MastersView.vue`, `ModelsPanel.vue`, `equipment.py` `_summary` / `_detail`, `dialogs.js`.
Sections not changed since round 1 were not re-reviewed.

## Round-1 answers verified in the text

| Finding | In the brief |
|---|---|
| BR1-01 | § 1 *Type or property*; § 4.6 table has 26 rows (counted) and the "No *Pump type* …" bullet; § 8.3 says 26; § 9.2 closed; decision 9; § 7.1 help line. |
| BR1-02 | § 2 bullet 2 (design = maker's rating, operating = reading, S036 = the item's nameplate); option lists marked *to verify* in bullet 1; § 11 glossary. |
| BR1-03 | § 5.1 `data_type` and `unit` rows, *The combined record*; § 8.2 tests. |
| BR1-04 | § 1.4, § 3.3, § 7.3 last bullet, § 7.4, decision 8, § 8.4 e2e. |
| BR1-05 | § 5.1 *Duplicates*: the two `UNIQUE_KEY_ERRORS` entries; `masters.py` lines 48–69 is the right place to copy (`UNIQUE_KEY_ERRORS.update({...})` at import). |
| BR1-06 | § 4.6 option statement; § 3.2 `SEED_CREATOR` kept, `_SEED_CREATORS` added. |
| BR1-07 | § 7.2 and § 7.3 *Wiring*. Checked: `useFormModal.send(request)` exists (lines 79–92) and `finish()` closes the modal then calls `afterSave`; `useMasterForm` re-exports `send` (line 47 is the comment naming the Team dialog); `modalError` tests `error.field in form.value`, so a form keyed by the literal `"values.12"` keeps it empty and `fieldError("values.12")` shows the message, as the brief says. |
| BR1-08 | § 5.1 option label; § 5.2 number form; § 5.3 shape and keys; § 5.4 last option; § 6.2 set and inactive class. |
| BR1-09–18 | Baseline line; § 5.2 normalised string; § 8.4 fit check on a model with properties; § 1.2 aligned; § 7.1 active count; § 4.6 descriptions; § 2 ISO 55001; § 3.2 `db_down` and `_TABLES` order. BR1-16 is in § 3.2 but not in § 8.2 (BR2-04). |

## Findings

### BR2-01 — minor — the edit dialog cannot disable *Data type* and *Unit*: the GET carries no "models hold values" flag, and the rule now also fixes the type when options exist

**Problem.** § 7.1 *Edit*: "Data type and unit are disabled when models hold values, with
the line 'Models hold values of this property, so its type and unit are fixed.'" Two gaps:
1. § 6.1's `GET /api/masters/properties` answers "every field, plus `options` … and
   `class_count`". Nothing says whether models hold values of the property, so the dialog
   cannot know when to disable the inputs.
2. BR1-03 made `data_type` fixed once the property has **any option or any value**
   (§ 5.1). § 7.1 still disables it only for values. A choice with options and no values
   shows an enabled *Data type*; the user changes it and gets the 409 on save. The help
   line is also wrong for that case (no model holds a value).

**Why it matters.** The coder either adds a field to the GET alone or leaves the inputs
enabled and lets the 409 do the work; both are decisions the brief should take.

**Options.**
- (a) **Recommended.** In § 6.1 add `value_count` (models holding a value of the property)
  to each list item, next to `class_count`; one `LEFT JOIN … COUNT` as `class_count`. In
  § 7.1: *Data type* disabled when `options.length > 0` or `value_count > 0`; *Unit*
  disabled when `value_count > 0`; the help line "Models hold values of this property, so
  its type and unit are fixed." when `value_count > 0`, else "A choice with options keeps
  its data type." when only options exist.
- (b) Keep the inputs enabled and rely on the 409 — a refusal after typing, for a rule the
  screen could have shown.

### BR2-02 — minor — which `equipment:edit` the card's button follows is not stated

**Problem.** § 7.4: "Users with `equipment:edit` see a button **Edit model values**."
`EquipmentDetailView.vue` has two different computeds for that key: `canEdit` (lines
48–50: the key at the **node's site**, from `node.permissions`, and not scrapped, not
loading) and `canEditModels` (line 53: the key at **any** site, from `userPermissions`,
"Model documents are maintained in Masters by equipment:edit held at any site"). The PUT
behind the button is checked as the union (§ 6.1), as the model documents are.

**Why it matters.** With `canEdit`, an engineer who holds the key at another site sees no
button on an item here, though the API would accept the save and Masters shows the same
dialog to him. With `canEdit` the button also vanishes on a scrapped item; the model's
values are not the item's, so that rule has to be chosen, not inherited.

**Options.**
- (a) **Recommended.** The button follows `canEditModels` (the union, as the model
  documents' *Managed in Masters* hint), on every lifecycle: the values belong to the model,
  and the dialog's title names the model. Say so in § 7.4.
- (b) `canEdit` — hides a save the API allows; and a scrapped item's page would lose a
  button that does not act on the item.

### BR2-03 — minor — the model dialog's values arrive by a GET after the dialog opens, so the dirty guard sees them as typed input

**Problem.** § 7.3 keys the form by `"values.<property_id>"` but does not say **when** the
form is filled. `useFormModal.open()` (lines 40–44) sets the snapshot in `nextTick`; a form
filled from `GET /equipment-models/<id>/properties` after that tick differs from the
snapshot, so `dirty` is true and *Cancel* on an untouched dialog asks whether to lose
input. `openEdit(record)` builds the form synchronously from `fromRecord(record)`; the
other dialogs have their record in hand (the store row).

**Why it matters.** The guard (S007) fires on every untouched close until the coder finds
the cause; the fix chosen alone could be a second snapshot path.

**Options.**
- (a) **Recommended.** Fetch first, open second: the *Properties* button awaits the GET,
  then calls `openEdit(answer)` with `fromRecord` building `{ "values.<id>": … }` from
  `answer.items`; a failed GET shows in the panel's `loadError` (and the card's own error
  line). The dialog then needs no loading state. Say so in § 7.3.
- (b) Open at once, fill on arrival, then call `markClean()` (exported, line 36) — a
  loading state in the dialog and a second place the snapshot is taken.

### BR2-04 — minor — § 8.2 still says `db_down` is local to `test_access_control_api.py`, contradicting § 3.2

**Problem.** § 8.2: "with a `db_down` fixture as in `test_access_control_api.py` (line 42;
it is local to that file, not in `conftest.py`)". § 3.2 (BR1-16, accepted) moves the
fixture to `conftest.py` and removes the two local copies. Checked for the move: the two
bodies are the same two `monkeypatch.setattr` lines on `db_helpers.ensure_schema` and
`access_control.ensure_schema` (`test_access_control_api.py` lines 42–47, `test_auth.py`
lines 63–68); only the docstrings differ. `conftest.py` already imports `access_control`;
it needs `import db_helpers`. `test_health.py` line 14 is a comment ("as test_auth's
db_down does"), not a use.

**Why it matters.** A coder reading § 8.2 writes a third copy in `test_properties_api.py`.

**Options.**
- (a) **Recommended.** § 8.2: "with the `db_down` fixture of `conftest.py` (§ 3.2)". Add
  to § 3.2's row for the two files: "the comment in `test_health.py` line 14 now names
  `conftest.py`".
- (b) Keep the copies and drop the § 3.2 move — three copies of one fixture.

## Nits

- **BR2-05** (nit) § 1 *Type or property*: the last sentence "The seed makes properties
  only. It links none to a class, because …" is item 5's text, left here when the paragraph
  was inserted (its second line is still indented as a list item). Move it back to item 5.
- **BR2-06** (nit) § 7.2 "(30+ properties on a phone)": the seed is 26 now; say "26 seed
  properties, more over time".
- **BR2-07** (nit) § 7.4: name what the card hands the dialog — `node.model_id` and
  `node.model_label` (both in the detail: `equipment.py` `_summary` lines 220–223) — and
  that the dialog emits `saved` → `load()`, as `EquipmentMoveModal` does (line 269).
- **BR2-08** (nit) § 5.3 "Send the values as a list": `values` is an object. "Send the
  values as an object" (API-only text; no screen sends anything else).
- **BR2-09** (nit) § 4.6 descriptions: "The maker's rating …" fits *Power*, *Speed*,
  *Voltage*; it misfits *Number of stages*, *Nominal size*, *Displacement*, *Fuel tank
  capacity*. "The maker's value, from the nameplate or the data sheet." fits all 17.

## Checked and found consistent

- **Seed count.** The § 4.6 table has 26 rows; § 1.5 and § 8.3 say 26; no row, option or
  text still names *Pump type*, *Motor type*, *Compressor type*, *Valve type* or *Execution*
  except the two places that say they are gone (§ 1, § 4.6).
- **Section cross-references.** Every § number cited in the changed text points at the
  right section (§ 4.5, § 5.3, § 5.4, § 7.1–§ 7.4, § 9.2, § 9.5); the Review log's section
  names match.
- **`UNIQUE_KEY_ERRORS`** (`api_common.py` line 25) is a module dict filled by
  `UNIQUE_KEY_ERRORS.update({...})` in each blueprint at import; `_integrity_error` (lines
  49–58) maps 1062 through it to a 409 with the field, and re-raises anything else. The
  brief's two entries and the "no pre-check query" rule follow the pattern. With
  `properties_bp` registered under `/api/masters` beside `masters_bp`, the module is
  imported by `app.py` and the entries are present.
- **`_SEED_CREATORS`.** `conftest.py` lines 145–146 and 160–161: `_SEEDED_TABLES` is a
  tuple and `SEED_CREATOR` one string used in the `DELETE … WHERE created_by <> %s` loop;
  a dict driving that loop is a two-line change, and `test_migration_v11.py` keeps its
  `SEED_CREATOR` import unchanged.
- **Combined record (§ 5.1).** The four cases a `PUT` can produce are covered: `unit` on a
  non-number (400), `data_type` leaving *number* (unit cleared), `data_type` with options or
  values (409), `unit` with values (409). No path reaches `chk_property_unit`.
- **Last active option (§ 5.4)** follows from § 5.1 ("needs at least one active option to
  be linked or given a value") without a new refusal; stated now.
- **Locks (§ 5.6)** still hold for the BR1-03 rule: an option insert locks the property row
  (2) first, so the "any option" check inside the property edit (which holds (2) `FOR
  UPDATE`) is serialised with it, as the values check is through the FK's shared lock.
- **Standards.** ISO 55001 clause 7.5 is *Information requirements* (in the 2014 edition and
  kept in the 2024 revision): the organisation determines what information about its assets
  it needs, with what quality and how it is kept; the brief's one line states it correctly
  and may drop "to verify: clause number". The BR1-02 rewrite is right: in ISO 14224
  Annex A the *design* values are the manufacturer's rated values and *operating* values are
  the service conditions, which Plan.MD § 6 keeps as readings.
- **e2e (§ 8.4).** `expectDialogFits` (`dialogs.js` lines 30–42) looks for
  `.modal-footer button[type=submit]` and a *Cancel* button, so the model-dialog check on a
  class with properties is the right condition; the new *Edit model values* check is a
  browser check and sits in *Automated*; § 8.5 "none" stays right.
- **UX of the changes.** The card button saves the Masters round trip (one tap, the same
  dialog, the title names the model so a kiosk user sees the scope); the data-type help line
  points at *Equip Type*, which is the toolbar label in `MastersView.vue` line 25; the
  class dialog's search box stays useful at 26 rows and more.
