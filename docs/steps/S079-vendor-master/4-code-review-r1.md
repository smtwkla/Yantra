```
Step: S079 — Vendor master
Doc: code-review r1
Author: code-reviewer (Opus 5.5)
Date: 30-10-2026
```

# S079 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step is built as the brief says. All three
unit suites, the build and the schema docs check are green. Two nits remain.

**What I reviewed.** I reviewed the working tree against the baseline `d216f48`, with
`git diff -w --ignore-cr-at-eol`. I left out the files that are not S079's, as the orchestrator
asked: `docs/Plan.MD`, `docs/roadmap/**`, `docs/steps/INDEX.md` and the folders `S080-*` to
`S084-*`. I read every code hunk, the new files `VendorsPanel.vue`, `test_vendors_api.py` and
`test_migration_v42.py` in full, and `create_person` / `update_person` in full.

## Tests run

All with `YANTRA_TEST_RUN=s079cr1`, 30-10-2026.

- `tooling\run-tests.bat`: **ALL SUITES: PASSED**. Backend 4170 passed (186 s), frontend 377
  passed, tooling 231 passed.
- `npx vite build` in `frontend/`: built in 4.5 s; only the existing chunk-size warning.
- `tooling\schema-docs.bat check`: **exit 0**, "Schema docs at migration v42: 4 passed"
  (`scratch/schema-docs-s079cr1.log`).
- Browser tests: I ran none. No finding of mine needs a re-run.

**The coder's browser runs.** The report names the right specs: `masters.spec.js` (the changed
screen), `floor.spec.js` and `tickets-raise.spec.js` (they open the Team dialog), and
`screens.spec.js`. The targeted run passed (72 passed, 2 skipped). The whole suite ran once at
Normal; one re-run had a stated reason. I checked the three whole-suite failures; none is S079's:

- `changelog.spec.js:14` (both cases, `it_admin` and `admin`): fact: `CHANGELOG.md` at `d216f48`
  has an empty `## 0.1.14 — 30-10-2026` section, from the release commit `e77d635`. The test's
  `getByText("This version")` then meets two elements. S079 changes neither `CHANGELOG.md`,
  `VERSION`, the sidebar nor the dialog (`git status` shows them clean).
- `improvements.spec.js:97` ("S068: … Closed is empty"): it expects an empty *Closed* list on the
  lane's shared database, so it depends on which tests share its lane. S079 changes no improvement
  code or screen. The coder's re-run of that spec alone passed.

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR1-01** (nit) `frontend/src/views/masters/VendorsPanel.vue:71`: with every vendor inactive
  and *Show inactive* off, the tab says "No vendors yet. Add the first one with *Add vendor*.",
  which is not true. Show it only when `vendors` is empty, and otherwise a line such as "No active
  vendors. Turn on Show inactive to see them." The manufacturers and trades panels share the
  pattern, so this can also wait for a pass over all of them.
- **CR1-02** (nit) `frontend/src/views/masters/PeoplePanel.vue:491`: the hint "No vendors yet; add
  one under Vendors." checks `vendors.length === 0`, so with only inactive vendors the select offers
  "No vendor" alone under the general help text. Test the active vendors instead
  (`vendorChoices`, without the person's stored one).

## Manual browser checks for the user

None. The brief's § 8.5 lists no real-device check, and its four browser checks are automated
(below).

## Checked and found consistent

- **Migration v42** (`local_db.py`): the SQL is the brief's § 4.1, in three statements with the
  `IF NOT EXISTS` forms. The comment states the missing precondition, the reason and the rollback
  limit. `_PRECONDITIONS` is unchanged; correct, because no existing row is converted.
  `test_migration_v42.py` covers every § 8.1 case, including the re-run and the half-applied
  CHECK.
- **Schema docs**: `notes.json` has the `vendors` line, the `people` line names `vendor_id` and
  `chk_people_vendor`, and the area note adds "vendors". `schema.json` and `schema-data.js` are
  generated; the check exits 0 at v42.
- **§ 5.1 rules**: `phone_parser(label)` (the orchestrator's accepted change) follows the
  pattern, the bounds, the clearing and the message of the brief. `_parse_phone` is
  `phone_parser("Phone")`, and a unit test checks that the label reaches the messages. The name
  reuses `_parse_manufacturer_name`. The 409 text is in `UNIQUE_KEY_ERRORS`. No DELETE route.
- **§ 5.2 rules**: `vendor_link_error` holds rule 1 in the pure core and picks the field as the
  brief says. `_check_vendor_link` uses the locked row's employment and vendor. A new link is
  checked by `_check_new_vendor` with `LOCK IN SHARE MODE`, and a re-sent stored vendor reads
  nothing. All eight PUT shapes are tested, with the stored row afterwards.
- **§ 5.3 locks**: person → vendor → trades in `update_person`, after the two 403s (BR1-03).
  `update_vendor` locks only its row. No vendor write takes a person lock, so no cycle. The module
  docstring and the Team block comment carry the order. No other code path writes
  `people.employment` or `people.vendor_id` (`git grep`), so the CHECK cannot answer a 500 on this
  release.
- **§ 5.4 permissions**: `GET` on `masters:read`; `POST` and `PUT` on `equipment:edit`; the phone
  removed by `_vendor_out` for readers without `equipment:edit`, tested per role. The link uses
  `people:edit`. No new key; `config_rbac.py` is unchanged. The actor comes from `actor()`, never
  from the body. All SQL uses parameters; the f-strings join only fixed text.
- **The people answer**: `_PERSON_SELECT` feeds both `list_people` and `_fetch_person`, the only
  callers of `_people_out`, so `vendor_active` is always present and becomes a boolean or `None`.
- **Database down**: the vendor routes use `get_db()`; `test_the_list_is_503_while_the_database_is_down`
  checks `GET` and `POST`.
- **Frontend**: `VendorsPanel.vue` follows `ManufacturersPanel.vue` (`FormModal`, `useMasterForm`,
  `ActiveToggle` with its plain confirm). The Team dialog's select shows only for *Contractor*;
  the `watch` clears it on *Direct employee*; `toBody` always sends `vendor_id`, so a dialog save
  never meets rule 1. The warning texts, the stored inactive vendor as "<name> (inactive)" and the
  list suffix match § 5.5. The new tab sits after *Trades*, before *Team*. No shared frontend file
  changed.
- **Use on the floor**: the dialogs use `FormModal`, whose body scrolls with a fixed footer.
  Deactivate is reversible and confirmed. Every new message is one or two short lines that say
  what to do. The table sits in `table-responsive`; `btn-sm` matches every other Masters panel.
  Every Masters reader holds `equipment:edit`, so *Add vendor* is shown to all of them.
- **Tests against § 8**: `test_vendors_api.py`, `TestVendorLink` in `test_people_api.py`,
  `TestVendor` and `TestVendorLink` in `test_masters_core.py`, `conftest.py` (`"vendors"` after
  `"people"`, `Uniq.vendor_name()`, `make_vendor`) and `masters.test.js` cover the brief's lists,
  with the failure modes. The four S079 browser tests assert what the user sees (row text, People
  count, warning text, options, the selected option) and call `expectDialogFits` on each dialog
  they open. None is tagged `@device`, which is correct: none is a layout check.
- **Manual checks**: the report's `## Manual checks` carries the three **important** checks and
  the fourth as `[auto]`, each with its test, plus the section-loop entry.
- **Scope and decisions**: nothing of the brief is missing, and nothing extra is built. Each
  departure (the factory, `_check_vendor_link`, the footnote shown only with rows, the local
  `postAsAdmin`, the split test cases) is in "Decisions taken".
- **Docs pass**: `Plant-Facts.md` § 4 lists the five vendors with no number or address, with a
  § 10 line; `.claude/CLAUDE.md` § SMTW-Review has the *Vendor link (S079)* point of § 9 Q3.
  `Plan.MD` needs no change; no secret, role or device check was added.
- **Track**: full; the step adds a migration, which the full track allows.

## Feedback

- hindrance: the diff to review had to be built by hand with `git diff d216f48` and a list of
  paths to leave out, because the step has no snapshot yet and the working tree also holds the
  orchestrator's S080–S084 and roadmap edits (about 2 min).
- idea: `step_snapshot.py diff` could take `--base <commit>` for a step not yet snapshotted, and
  leave out the other step folders by default, as it does for a snapshotted step.
