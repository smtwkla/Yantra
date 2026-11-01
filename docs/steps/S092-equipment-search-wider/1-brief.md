```
Step: S092 — Find a machine by model, maker or class, and confirm it
Doc: brief
Author: Orchestrator (Opus)
Date: 01-11-2026
Track: light
Status: Gate B 01-11-2026 (code review r1: 1 minor, 1 nit, fixed in fix round 1, tests only); approved 01-11-2026 by KLA (1a: Q1 (a), words in any order); brief review r1: 0 blocker, 0 major, 3 minor, 8 nits — all accepted
Baseline: 14d7e0b
```

# S092 — Find a machine by model, maker or class, and confirm it

KLA, 01-11-2026: "In many dialogues / forms, we need to select equipment. This needs the user to remember the
code." The search box on Raise ticket already finds a machine by code, name, manufacturer, model, type and notes
(`backend/equipment.py:645-649`), but its hint says only "Code or name", it does not search the class, and the
text must match as one piece. KLA chose (01-11-2026): (a) a hint that names what can be typed; (b) the class in
the search, not the unit names; (c) more detail on each match; and a link to the equipment page after the pick, to
confirm the machine or see more. A separate finder dialog with a *Select* button is not built now (§ 1 Out of scope).

## 1. What will be built

1. **The search finds the class too.** The equipment search (`q` on `GET /api/equipment`, function
   `list_equipment`) also matches the class name and the class code (`c.name`, `c.code`; the class is already
   joined through `NODE_JOINS`). Unit and site names stay out (KLA).
2. **Words in any order** (Q1: (a), KLA 01-11-2026, to confirm at gate A). The search text is split at whitespace
   (`str.split()`, so a tab or line break in a paste splits too). A node is found when **every** word matches at
   least one of its fields: code, name, notes, type name, class name, class code, manufacturer name, model
   designation. So `press 250` finds "250T Hydraulic press", and `atlas ga37` finds the Atlas Copco GA37
   compressor. Empty text, or only spaces, means no search (as today). At most **8** words are used
   (`MAX_SEARCH_WORDS`, in `backend/equipment.py` beside `list_equipment`); words after the eighth are ignored,
   so a long paste cannot build a huge query. The cap is a guard; the user is not told about it. Each word keeps
   today's escaping of `%` and `_` (`like_pattern`).
3. **One hint for the three search boxes.** The shared search box (`frontend/src/components/EquipmentPicker.vue`,
   used on Raise ticket, the Readings register and the contract's Add machine) keeps its label *Equipment*.
   - Placeholder in all three boxes: `"Code, name, model or class"`; the Equipment list's box
     (`EquipmentView.vue`) adds notes: `"Code, name, model, class or notes"`; Move › New parent
     (`EquipmentMoveModal.vue`) uses the first form.
   - Below the picker's box, while there is no result yet (`v-if="!results"`), one line: *"You can also type the
     manufacturer, or several words in any order."*
   - The "more found" lines (`EquipmentPicker.vue:81`, `EquipmentMoveModal.vue:177`) both become
     `"More found — add a word, such as the model or class."`
4. **More detail on each match** (`EquipmentPicker.vue`). Each match keeps its first line `code — name`, and its
   second line, the full path. A third line shows what the list row already sends (`_summary`), laid out
   `d-flex flex-wrap align-items-center gap-2 small`: the model label (`model_label`, when the node has a model),
   the class code, `LifecycleBadge`, `CriticalityBadge` (with `effective_criticality`; the badges as on the
   Equipment list's phone cards, `EquipmentView.vue:509-510`). A long maker name wraps; the row stays one tap
   target. No new data is fetched.
5. **A link to the equipment page after the pick.** Where the picked machine shows, an *"Open equipment page"*
   link opens `/equipment/<id>` **in a new tab** (`target="_blank" rel="noopener"`, as `EquipmentDetailView.vue:350`),
   so the half-filled form is kept. Style `btn btn-outline-secondary`, as the Readings register's (`:181`):
   - Raise ticket: on the machine card, beside *Change* (`RaiseTicketView.vue`); on a phone both buttons wrap under
     the `code — name` text (the card is `d-flex flex-wrap`);
   - contract › Add machine: in the `picked-machine` block, beside *Change*, both `btn-sm`
     (`ContractMachineDialog.vue`).
   The Readings register already has this link (`ReadingsRegister.vue:181`, same tab, no form to lose); it is
   not changed.

**Out of scope:** a finder dialog (a *…* button, browse by unit, a details view and *Select*): kept as an idea
if the floor still needs it after this step; the unit and site names in the search (KLA); the Move dialog's own
search code (it calls the same route, so it gains items 1 and 2; making it use `EquipmentPicker` is a tidy-up for
later); the Parts panel's *Fitted to* dropdown (a short list of the ticket's machine and its parts).

## 2. Standards and practice

- **ISO 14224** (equipment data for reliability and maintenance) defines the equipment *taxonomy*: each item has
  a class and type, and attributes such as manufacturer and model. Searching by those attributes lets a person
  name the machine the way they know it. Showing class, model and path before and after the pick helps record the
  failure against the right item, which ISO 14224 treats as part of data quality. Clauses (from memory, to verify
  against the text): 7 for the taxonomy, 8 and Annex A for the equipment attributes, 6 for data quality.
- **TPM, autonomous maintenance**: the operator raises the ticket. A search that works without the code removes a
  reason to skip reporting or to report on the wrong machine.

## 3. Where

| File | Change |
|---|---|
| `backend/equipment.py` | `list_equipment`: split `q` into words (at most `MAX_SEARCH_WORDS` = 8); one `AND`-ed condition per word over the eight fields of § 1.2 |
| `backend/tests/test_equipment_api.py` | new tests (§ 5); the existing search tests stay green unchanged |
| `frontend/src/components/EquipmentPicker.vue` | placeholder, the hint line, the "more found" line, the third line of each match |
| `frontend/src/views/EquipmentView.vue` | placeholder only |
| `frontend/src/views/equipment/EquipmentMoveModal.vue` | placeholder and the "more found" line |
| `frontend/src/views/RaiseTicketView.vue` | *Open equipment page* link on the machine card |
| `frontend/src/views/contracts/ContractMachineDialog.vue` | *Open equipment page* link in `picked-machine` |
| `frontend/e2e/tickets-raise.spec.js`, `frontend/e2e/contracts.spec.js` | new tests (§ 5) |

**Docs (housekeeping, by the coder):** `docs/Plan.MD:315` (the equipment notes line, "searchable"): name what the
search finds (code, name, notes, type, class, manufacturer, model; words in any order); `docs/steps/device-checks.md`
(one row, § 5). No migration, so no schema docs.

## 4. Design decisions

- **Every word must match some field (AND of words, OR of fields)**, rather than the whole text as one piece.
  Rejected: keep one piece and add the class only; then `press 250` still finds nothing. Rejected: a full-text
  index; it needs a migration, ignores short words and parts of words, and is more than ~50 users need.
- **The matches only grow.** Text that matched one field as one piece still matches: each of its words matches
  that field, and a word that matched the old `CONCAT(mf.name, ' ', m.designation)` matches `mf.name` or
  `m.designation` alone. No existing backend or browser test expects no match, or an exact count, for a text of
  several words (checked in brief review r1).
- **The change sits in the route, so every screen gains it**: Raise ticket, Readings register, Add machine, Move
  and the Equipment list. Rejected: a separate picker-only search; two search rules for one list would confuse.
- **The link opens a new tab.** Rejected: the same tab; leaving Raise ticket loses what was typed, and the
  contract dialog would close. Rejected: details inside the form; that is the finder dialog, out of scope.
- **The third line uses what the list already sends**; no extra request per match.

## 5. Tests and acceptance

**Backend** (`backend/tests/test_equipment_api.py`, beside `test_search_finds_the_type_name`):
- `test_search_finds_the_class_name_and_code`: a node of a class named e.g. "Hydraulic press <unit code>" is
  found by `q="hydraulic press"` and by the class code; another node at the unit is not.
- `test_search_words_in_any_order`: name "250T press": `q="press 250t"` finds it; `q="press 999"` finds nothing.
- `test_search_words_across_fields`: `q="<manufacturer word> <name word>"` finds the node (one word per field).
- `test_search_uses_at_most_eight_words`: nine words where only the ninth matches nothing: the node is still found.
- The existing tests stay unchanged and green: `test_search_escapes_wildcards` (`" A_B "` is one word),
  `test_search_matches_code_and_name`, `test_search_by_designation_and_by_manufacturer`,
  `test_search_finds_a_word_in_the_notes`, `test_search_finds_the_type_name`,
  `test_removed_documents_api.py:102` (`q` = a node code).

**Browser** (logic device `phone-chromium`, untagged):
- `tickets-raise.spec.js` "S092: …": type `600 vah` (the seed extruder's model is "Haendle GmbH VAH 600",
  `tooling/e2e/seed_e2e.py:56`; the machines the tests make by API use "Atlas Copco GA37", so this finds the
  extruder alone on every lane); its match shows the class code and the model; click it by `^<code> — ` as
  `tickets-raise.spec.js:59` does; the card's *Open equipment page* link has `href` `/equipment/<id>` and
  `target="_blank"`. Existing lines stay valid: they fill by name and click `^<code> — `; the label stays
  `"Equipment"` (`screens.spec.js:62`, `readings.spec.js:940`, `contracts.spec.js:319`…`410`).
- `contracts.spec.js` "S092: …": after a pick, `picked-machine` holds the link with the same `href` and target;
  `expectDialogFits` after the pick (the block gains a second button).
- Targeted run: `tickets-raise.spec.js`, `contracts.spec.js`, `readings.spec.js`, `equipment.spec.js`,
  `screens.spec.js`.

**On a real device** (device-checks row; IT Admin; internal Wi-Fi; production on the TEST machine, or the dev
server on KLA's laptop):
- **important**: in the installed app (PWA) on an Android phone and an iPhone, tap *Open equipment page* on Raise
  ticket, look at the page, return to the app: the half-filled form is still there. What to expect (assumption,
  which this check verifies): Android opens the page in a tab over the app with a close cross; an iPhone (iOS 13
  and later) opens an in-app sheet with *Done*. A page shown "inside" the app is the right result.

## 6. Open questions and assumptions

- **Q1 (KLA, 01-11-2026: (a), confirmed at gate A):** match the words in any order (§ 1.2). (a) yes: `press 250` and `atlas ga37`
  work; the Equipment list's search changes the same way. (b) no: the text stays one piece and only the class is
  added; the hint's second sentence, the three any-order backend tests and the any-order browser text would go.
  KLA answered "Ok" to the recommendation; confirmed at gate A.
- Assumption: equipment codes already carry the class code in most cases, so the class code adds few new matches;
  it is cheap and kept for codes that do not.
- Assumption: 8 words are enough; a person types 1–3.

## 7. Amendments

None.

## Review log

| Finding | Answer |
|---|---|
| BR1-01 (minor) Q1 says nothing of what (b) removes | Accepted: KLA answered (a) on 01-11-2026; § 6 now names what (b) would remove, and §§ 1, 5 are written for (a) |
| BR1-02 (minor) "More found" lines still say code or name | Accepted, option 1: both lines read "More found — add a word, such as the model or class." (§ 1.3, § 3) |
| BR1-03 (minor) device check names no network; PWA behaviour | Accepted, options 1 and 2: internal Wi-Fi, and what Android and iPhone show (§ 5) |
| BR1-04…BR1-11 (nits) | Accepted: `str.split()` and where the cap lives (§ 1.2); the third line's layout, badges cited only (§ 1.4); link style and `rel="noopener"`, `expectDialogFits` (§ 1.5, § 5); `600 vah` (§ 5); ISO 14224 clauses, to verify (§ 2); one placeholder form (§ 1.3); hint only while no result (§ 1.3); `Plan.MD:315` (§ 3) |
