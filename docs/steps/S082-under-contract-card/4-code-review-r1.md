```
Step: S082 — Under contract on the machine
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S082 — code review, round 1

**Verdict: no blocker or major finding is open.** One minor finding (the call-out link's tap target) and one nit.
The permissions hold as the brief asks. The unit suites, the build and the schema docs check are green.

## Tests run

Run name `YANTRA_TEST_RUN=s082cr1`.

- `tooling/run-tests.bat`: backend PASSED, 4355 passed (238 s); frontend PASSED, 397 passed; tooling PASSED,
  231 passed; ALL SUITES: PASSED.
- `npx vite build` in `frontend/`: built in 5 s, only the known chunk-size warning.
- `tooling/schema-docs.bat check`: exit 0, "Schema docs at migration v44: 4 passed" (164 s).
- Browser: none re-run. CR1-01 is a CSS fact (below) and needs no run. The coder's runs are in the impl report:
  the new tests alone 8 passed; targeted (`contracts`, `equipment`, `lessons`, `screens`) 112 passed, 2 skipped;
  the whole suite at Normal 345 passed, 15 skipped, 2 failed. The 2 failures are the S048 changelog tests
  (`changelog.spec.js:14`), a known fault in HEAD outside S082 (the empty `## 0.1.14` section). The targeted set
  is the right one: the changed screens (`contracts.spec.js` holds the S082 tests, `equipment.spec.js` the list
  and its filter row, `lessons.spec.js` the card order) plus `screens.spec.js`. No shared file changed
  (settings: *Shared code*).

## Findings

### CR1-01 (minor) — the call-out link is not a 44 px tap target

- **Where:** `frontend/src/views/equipment/UnderContractCard.vue:98`.
- **Problem:** the `tel:` link has `class="tap-target"`, which sets only `min-height: 44px`
  (`frontend/src/assets/main.css:142`). The `<a>` is an inline element, and CSS ignores `min-height` on a
  non-replaced inline element. So the link keeps the height of one text line, about 24 px. The *Open contract*
  link on line 100 works, because it also has `d-inline-block`.
- **Failure scenario:** an engineer at the machine, with gloves, taps the number to call the vendor. The tap
  lands just above or below the text and nothing happens; the engineer types the number by hand. The tap-to-call
  link is the reason BR1-04 asked for it (S064's 44 px rule for floor controls).
- **Fix:** add `d-inline-flex align-items-center` (or `d-inline-block`) to the link, as *Open contract* has.
  Optionally assert it in the first S082 test: the link's `boundingBox().height` is at least 44.

## Nits

- **CR1-02** (nit) `frontend/src/views/equipment/UnderContractCard.vue:96`: drop `&& !r.ended`, because
  `callLine` already returns `null` for an ended item; and take `ended` on line 43 from the same helper as
  `contractLabels.js` (`isEnded`, exported), so the rule lives in one place.

## Checked and found consistent

- **Permissions (§ 5.6).**
  - The card route has `require_perm("contract:read_basic")`; a role without it anywhere gets 403
    (`test_no_read_basic_anywhere_is_403`, the key patched); no identity gets 401.
  - The node is read by `load_node_for_user(…, for_update=False)`: 404 outside the reader's units and for a
    missing node, the same answer.
  - Each contract is kept only where `has_perm_at("contract:read_basic", site)` holds at the contract's site,
    once per site. The moved-machine residual is tested (`test_a_contract_at_a_site_the_reader_holds_no_role_at`).
  - The item goes through `_contract_out` with `_SiteFlags().at(contract site)`, so `callout_number` goes out
    only with `contract:read` at the contract's site. Then only `_CARD_KEYS` are kept: no `price`, `price_total`,
    `priced_count`, `machine_count`, `cost_note`, `can_edit` or `can_read_cost`, for any reader. The test checks
    all seven keys for the technician, the engineer and the manager, with a priced line and a cost note.
  - The list filter takes its sites from `auth_utils.sites_holding(cur, "contract:read_basic")`; with no site it
    gives `0 = 1` / `1 = 1`, no empty `IN ()`. The test with the patched key proves a contract at a site without
    the key does not count.
  - The *Contract* select shows only with `contract:read_basic` in `userPermissions`, and `keyApplies` keeps a
    bookmarked `?contract=` out of the URL and the count for anyone else.
  - No new key; `test_role_matrix` is unchanged. The SQL uses placeholders only (`marks`, `%s` lists).
- **`sites_holding`** is moved unchanged to `auth_utils.py`; both callers in `contracts.py` (`list_contracts`,
  `_detail`) use it; `equipment.py` imports only `contracts_core`, never `contracts.py` (B10).
- **The card's rows (§ 5.1, BS1-01).** One plain read on `_CONTRACT_COLUMNS` + `_CONTRACT_FROM` (the old
  `_CONTRACT_SELECT` text, unchanged) with `contract_equipment cl`; active, from date, the 90-day window. The pure
  `card_items` keeps the nearest line and the order of the brief; its tests cover the edge days (90 kept, 91
  dropped; starting today kept, tomorrow dropped) and the order with ties by `id`.
- **The filter (§ 5.4).** In `list_equipment` beside `tickets`, not in `_list_filters`; the asset-list test proves
  the print ignores it. `covered_sql`'s `p.parent_id` is `NODE_JOINS`' parent alias; the parameters follow the
  SQL's order. An empty `?contract=` is 400, as BS1-05 says.
- **The card (§ 5.3).** Fetched only with `contract:read_basic` in `node.permissions`; hidden with no item except
  for a `contract:edit` holder at the node's site; the error text; the D9 warning first, in `alert-warning` with
  `role="alert"`; the headline and *Ends in N days* badge; the via line; the response line left out on `null`; the
  coverage lines; the call line left out when ended or under the warning for a non-reader; *Open contract*;
  `text-secondary` for an ended item. Placed after *Lessons* and before *Open tickets*, `order-0`, in the page's
  flex column. A stale answer after a node change is dropped by `loadSeq`.
- **The departures** in the report's *Decisions taken* are all listed and sound: `via.level` for the
  component-unit wording; the select split into columns and joins (no near-copy); `callLine` returning `null`;
  the texts as exported constants; `keyApplies` (the same keys as before, plus `contract`); the card as its own
  root. The three gate-B items (the place, "To call the vendor, ask the engineer.", the `tel:` link) are the
  brief's own, flagged for KLA.
- **Edge cases.** A machine has no ancestors (`NULL`s dropped before `IN`); the same contract on the node and its
  parent is one item; an inactive, an ended and an upcoming contract do not count in the filter; the database
  down gives 503 (`db_down`). No writes, so no locks.
- **Tests against § 8.2 and § 8.4.** Every listed case has a test. Each automated check asserts what the user
  sees: the warning text, the headline, the coverage lines, the number's absence, the `href`, the contract page's
  heading, the vertical order by bounding boxes, the rows in and out of the filtered list. Only the fit test has
  `@device`, by the rule (its title names the fit). No test opens a dialog, so no `expectDialogFits` is due.
- **Screen text (scope B).** The texts are short and plain; the button-free card has one verb link
  (*Open contract*). The error line follows the *Lessons* card's form.
- **Docs pass.** `docs/Plan.MD` § 4.1 has the card and the filter, and its text matches the code;
  `.claude/CLAUDE.md` § SMTW-Review *Contract fields by key* gains the S082 sentence of § 8.6; the device-check row
  59 is in `docs/steps/device-checks.md` with its set-up; no migration, so `docs/schema/` is unchanged and the
  check exits 0. No role, secret or plant fact changed.
- **Manual checks.** The impl report's `## Manual checks` holds all four important automated checks as `[auto]`
  with their tests and the important real-device check as an unticked box with its row.
- **Track:** full, as the brief says.

## Manual browser checks for the user

- Device-check row 59: on a phone, scan the TEST label on the dev server as a technician and read the yellow
  "Do not repair" warning at arm's length in the shop's light (IT Admin; set-up by KLA in the row).
- After CR1-01's fix, as an engineer on a phone, tap the call-out number: the phone's dialler opens with the
  number.

## Feedback

- waste: `tooling/schema-docs.bat check` took 164 s in a step with no migration and no `docs/schema/` change; the
  round could skip it when the step's diff touches neither `local_db.py` nor `docs/schema/`
  (`scratch/schema-docs-s082cr1.log`).
- idea: the comment on `.tap-target` in `frontend/src/assets/main.css:139` could say that it needs a block or
  inline-block element, since `min-height` does nothing on an inline link (CR1-01; a reviewer has to know it).
