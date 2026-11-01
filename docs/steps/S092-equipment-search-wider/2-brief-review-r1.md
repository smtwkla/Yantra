```
Step: S092 — Find a machine by model, maker or class, and confirm it
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 01-11-2026
```

Reviewed against: 14d7e0b (no step's code is uncommitted; only `docs/steps/INDEX.md` and this step's folder)

**Verdict: no blocker or major finding. Three minor findings and eight nits.** The brief fits the light track
(no migration, no permission or locking change, the same route and the same components, nine files), so this is the
only review round. The hard checks the orchestrator asked for are all in order; the details are under *Checked and
found consistent*. Facts file used: `scratch/brief-facts-S092.md`.

## Minor

### BR1-01 — minor — § 6 Q1: the brief does not say what option (b) takes out of §§ 1, 5

**Problem.** Q1 is KLA's decision at gate A, but the brief is written for (a) only. Under (b) three things change
that the brief does not name: the hint's second sentence ("…or several words in any order") goes; the three (a)-only
backend tests (`test_search_words_in_any_order`, `test_search_words_across_fields`,
`test_search_uses_at_most_eight_words`) and the "words in any order" part of the Raise ticket browser test go; and
the `CONCAT(mf.name, ' ', m.designation)` field must stay as one field, since under (b) "Atlas Copco GA37" is still
matched as one piece (`test_search_by_designation_and_by_manufacturer`, its third assertion).

**Why it matters.** KLA decides between (a) and (b) from the brief; the cost of (b) is not visible, and a coder given
(b) would have to work out the three changes alone.

**My review of the two options** (the decision is KLA's):
- (a) *every word must match some field*. This is how every search box people use works (a phone's contacts,
  a web search), so a floor user needs no explanation. I checked the brief's claim that matches only grow: a
  word has no space in it, so a word that matched the whole text matches the same field, and a word that matched
  the CONCAT field matches `mf.name` or `m.designation` on its own. No existing backend or browser test expects
  no match, or an exact count, for a text of several words (the list is under *Checked and found consistent*).
  Cost: the two "More found" lines need new wording (BR1-02).
- (b) *one piece plus the class*. The smallest change; `press 250` still finds nothing, and the hint can only
  say "Code, name, model or class". Its one merit is that nothing about the search moves for the Equipment list's
  users, who today type a code prefix.

**Options.** (1) ★ Add one line under Q1: "If (b): the hint's second sentence, the three (a)-only backend tests and
the any-order part of the browser test are dropped; the CONCAT field stays as one field." (2) Decide Q1 before the
brief goes to gate A and remove the other option from §§ 1 and 5.

### BR1-02 — minor — § 1.3: the two "More found" lines still say "type more of the code or name"

**Problem.** `EquipmentPicker.vue:81` shows "More found — type more of the code or name." and
`EquipmentMoveModal.vue:177` "More matches — type more of the code or name to refine the search." The brief changes
the placeholders of both boxes but not these lines. Under (a) the natural way to narrow is to add a word (the model,
the class), which the lines do not say; they also still name only code and name.

**Why it matters.** Scope B: the message tells the user what to do next, and after this step it tells the wrong
thing. The person who typed `press` and sees 20 presses is the one who needs the line.

**Options.** (1) ★ Under (a): both lines become "More found — add a word, such as the model or class." (one form
for both boxes). (2) Under (b): "More found — type more of the code, name, model or class." (3) Leave them; the
step is then half done for the one case the line is for.

### BR1-03 — minor — § 5 On a real device: the row names no network, and the PWA behaviour is worth a line

**Problem.** The device check names the account (IT Admin) and where (production on the TEST machine or the dev
server) but not the network (internal Wi-Fi or outside), which the rules ask for
(`docs/steps/device-checks.md` rows carry all three).

**Why it matters.** IT Admin reads the row alone; "the dev server" from outside is not reachable, and the check
on the TEST machine from the internal Wi-Fi is the one that matters.

**For the brief, labelled assumption** (from how the two platforms behave, not verified here, which is why the
device check is right to be *important*): in an installed Android PWA a `target="_blank"` link to the app's own
scope opens in a Chrome Custom Tab over the app, with a close cross; closing it returns to the app with its state.
On iOS 13 and later a standalone web app opens such a link in an in-app browser sheet with *Done*; older iOS
versions switched to Safari and the form was lost on return. In the plain browser on either phone, Back closes the
new tab and returns to the parent tab.

**Options.** (1) ★ Add the network: "internal Wi-Fi; production on the TEST machine, or the dev server on KLA's
laptop". (2) Also say what to expect (the custom tab / the in-app sheet) so IT Admin knows that a page shown "inside"
the app is the right result, not a fault.

## Nits

- **BR1-04** (nit) § 1.2: "split at spaces" → "split at whitespace (`str.split()`)", so a tab or a line break in a
  paste splits too; say where `MAX_SEARCH_WORDS` lives (`backend/equipment.py`, beside `list_equipment`, is right:
  one use) and that the cap is a guard the user is never told about. The cap wording itself is clear.
- **BR1-05** (nit) § 1.4: `EquipmentView.vue:509-510` shows the two badges and the unit, not the model label or the
  class code (the model is the table's column at :484, md and up). Cite it for the badges only, and give the third
  line's layout in one line: `d-flex flex-wrap align-items-center gap-2 small`: model label (when present), class
  code, `LifecycleBadge`, `CriticalityBadge`, so a long maker name wraps and the row stays one tap target.
- **BR1-06** (nit) § 1.5: say the link's style: `btn btn-outline-secondary` as the Readings register's (`:181`),
  `btn-sm` beside the `btn-sm` *Change* in `ContractMachineDialog.vue:108`; on a phone both buttons wrap under the
  `code — name` text in the Raise ticket card (`d-flex flex-wrap`, `:307`). Add `rel="noopener"` as
  `EquipmentDetailView.vue:350` does, for the same reason. The contracts browser test calls `expectDialogFits` after
  the pick, since `picked-machine` gains a second button.
- **BR1-07** (nit) § 5 browser test: name the words to type. The seed extruder's model is "Haendle GmbH VAH 600"
  (`tooling/e2e/seed_e2e.py:56`, `seed_dev.py:79`), and every machine the tests make by API uses "Atlas Copco GA37"
  (`contracts.spec.js:284`, `equipment.spec.js:262`), so `600 vah` finds the extruder alone on every lane; click it by
  `^<code> — ` as `tickets-raise.spec.js:59` does. Under Q1 (b) the text is `VAH 600`.
- **BR1-08** (nit) § 2: replace "clause number: to verify". ISO 14224:2016 puts the taxonomy in clause 7
  (*Equipment boundary, taxonomy and time definitions*), the equipment attributes (manufacturer, model) in clause 8
  and Annex A (*Equipment-class attributes*), and data quality in clause 6 (*Quality of data*) — a recommendation
  from memory, to check against the text before it goes into Plan.MD.
- **BR1-09** (nit) § 1.3: three wordings for one search ("Code, name, model or class", "Search code, name, model,
  class, notes…", "Search by code, name, model or class…"). One form in all three boxes, e.g. "Code, name, model or
  class" (the list's may add "notes"), keeps one term for one thing.
- **BR1-10** (nit) § 1.3: show the picker's hint line only while there is no result (`v-if="!results"`), so inside
  the contract dialog (`modal-fullscreen-sm-down`, the keyboard up) the hint does not take a line from the list once
  the user has typed.
- **BR1-11** (nit) § 3 Docs: Plan.MD names the search once, at `:315` ("Notes: free text for reading, searchable");
  the coder adds the words a search finds there (code, name, notes, type, class, maker, model; words in any order
  under (a)), so "(if it does)" can go.

## Checked and found consistent

- **Matches only grow** (§ 4): proof above (BR1-01). Every existing search test keeps its result:
  `test_search_escapes_wildcards` (`" A_B "` strips to one word; `"   "` is still no search; `0%` is escaped),
  `test_search_matches_code_and_name`, `test_search_by_designation_and_by_manufacturer` (each word of the label
  matches `mf.name` or `m.designation`), `test_search_finds_a_word_in_the_notes`, `test_search_finds_the_type_name`,
  `test_removed_documents_api.py:102` (`q` = a node code, one word). The class fields add no false match to them:
  test class codes are four letters (`conftest.py:325`) and the class name is "Test class", and no existing search
  word is a substring of either.
- **Browser tests with a several-word `q`**: `equipment.spec.js:164-187` (`E2E light <tag> <project>`: every word is
  in its three rows only), `:239` (a name with a unique tag), `contracts.spec.js:319`, `:396`, `:410` (a unique tag),
  `:369-370` ("No equipment found" for a BRICKS machine the engineer cannot see: the unit filter, not the text, keeps
  it out), `tickets-raise.spec.js:58-101` (`E2E extruder`, then the `^code — ` click). `tickets-work.spec.js:533`,
  `:551` are the tickets search, another route. None expects no match or an exact count that the change can move.
- **The Move dialog and the Equipment list use the same `q`**: `EquipmentMoveModal.vue:71` calls
  `/api/equipment?level=…&q=`, and `EquipmentView.vue:207-225` sends its `q` to the same route; `list_equipment` is
  the one place the text is matched (`equipment.py:641-649`). The brief's "the other two search boxes on the same
  route" holds; no e2e test exercises the Move dialog's parent search, so none breaks.
- **`target="_blank"` router-links** are an existing pattern in `RaiseTicketView.vue:320` and `:446`; Vue Router's
  link skips its own navigation when `target` is set, so the browser opens the tab. The Readings register's link
  (`ReadingsRegister.vue:181`) is same-tab, as the brief says.
- **The third line's data** is already in the list row: `_summary` (`equipment.py:288-306`) sends `model_label`,
  `class_code`, `effective_criticality` and `lifecycle`; no new request. `LifecycleBadge` shows "In service" for
  most rows, as the Equipment list's phone cards do; the brief follows that pattern knowingly.
- **Layers**: the rule (words, fields, cap) stays in the route's one `if q:` block, as today; the frontend only
  shows what the row sends. No new helper, no new abstraction.
- **Light track**: all five criteria hold. **Manual checks**: the one device check is rightly a device check (how
  the installed app returns to a half-filled form is nothing a browser engine judges); the automated checks are
  automated.
- **Standards**: ISO 14224 (taxonomy and equipment attributes: a machine is found by the data the standard asks to
  keep) and TPM autonomous maintenance (the operator reports without a code) are the right two; the clause
  placeholder is BR1-08.
- **Use on the floor**: one main job per screen is kept (the picker shows more on each match, and the extra link is
  one tap, reversible, away from Save); the picker's rows stay one tap target each; the hint wording keeps
  "manufacturer", the word the equipment page uses, so the app stays with one term.

## Feedback

- idea: "Themes dropped at the last triage — do not report them again" cost a read of the 65-row 31-10-2026
  section of `docs/steps/feedback-log.md`, whose one-line rows were cut at 200 columns and still hid the Theme and
  Decision cells; the spawn prompt could list the dropped themes in one line (1 call, about 40 KB spooled).
- waste: the facts file's *Screen text in the tests* lists `" A_B "` (a test value the brief quotes) and
  `"Equipment"` (44 lines) as screen text; neither needed checking (`scratch/brief-facts-S092.md:103-107`).
