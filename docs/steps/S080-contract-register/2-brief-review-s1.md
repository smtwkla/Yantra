```
Step: S080 — Contract register
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R02.1
```

Reviewed against: d216f48 + uncommitted S079 (`refs/steps/S079` = 73f0bc5; the diff read with
`step_snapshot.py diff S079` for the files the orchestrator named)

# S080 — Staleness review, round s1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding and five nits. Every
statement the brief makes about S079's code holds, except the ones below. The one question of this
review: does each statement about the changed files still hold? The facts file
`scratch/brief-facts-S080.md` was given, made on the working tree with S079 in it, and used.

## Findings

### BS1-01 — minor — § 5.2, § 5.6, § 8.2: S079 now has the vendor check S080 plans to write again, with other texts

**Problem.** S079 coded `masters._check_new_vendor(cur, vendor_id)` (`backend/masters.py`, after
`_check_vendor_link`): `SELECT name, active FROM vendors WHERE id = %s LOCK IN SHARE MODE`, then a 400
on `vendor_id` with "That vendor no longer exists. Reload and try again." (missing) or "Vendor
<name> is inactive. Choose another vendor or reactivate it." (inactive). § 5.2 of the brief plans the
same read in `contracts.py`, with one text for both cases: "Choose a vendor. The list holds the
active vendors of Masters › Vendors." At the baseline S079 was not coded, so the brief could not
reuse it.

**Why it matters.** Two copies of one check (CLAUDE-COMMON § DRY), and two refusals for one event in
one app (scope B: the same word for the same thing). S079's texts are also the better ones: they
tell the user which case it is and what to do.

**Options.**
- (a) **Recommended.** S080 makes the helper public in `masters.py` (`check_active_vendor`, the one
  rename; S079's two person routes call it through `_check_vendor_link`, unchanged), imports it in
  `contracts.py`, and takes S079's two texts. The § 5.1 `vendor_id` parser becomes `id_parser("Vendor")`
  ("Choose a vendor."; no parser of its own). § 5.2, § 5.6 steps 3, § 8.2 ("the message of § 5.2") and
  § 8.4's inactive-vendor test follow. The lock order is unchanged: the vendor is still read
  `LOCK IN SHARE MODE` after the contract or site lock.
- (b) Keep the copy in `contracts.py` but use S079's two texts.
- (c) Keep the brief as written: two texts for one refusal.

### Nits

- **BS1-02** (nit) § 5.1 `callout_number`, D11: S079's `phone_parser` runs `_collapsed`, so inner runs
  of spaces become one, not only "trimmed"; say so. Its rule text is the constant
  `masters_core.PHONE_RULE`; name it, so `test_contracts_core.py` compares against the constant, not a
  copy of the sentence (S079's impl report § 4 made it a constant for that).
- **BS1-03** (nit) § 3 Tests, § 8.1: the nearest pattern is now `backend/tests/test_migration_v42.py`
  (`V42 = … range(20, 43)`, `VERSIONS = list(range(20, 43))`, plus a half-applied re-run test), not
  `test_migration_v41.py`; v43 slices `range(20, 44)`. Checked: v42's ranges close at 43, so v43 breaks
  no migration test (§ 8.3 holds).
- **BS1-04** (nit) § 5.5: `backend/masters.py:1143` for `grantable_site_ids` is now
  `backend/masters.py:1212` (S079 added lines above it). Anchor by name, as § 3 says for this file.
- **BS1-05** (nit) § 3 Docs: S079 put `vendors` in the area *Team and access* of
  `docs/schema/notes.json` (its note now reads "People, trades, vendors, …"); the brief puts
  `contracts` under *Equipment*. Keep *Equipment* (R02.2's `contract_equipment` joins it to the
  register, and a contract is a site record), but say in one line that it differs from the vendor's
  area on purpose, so the coder does not pick.
- **BS1-06** (nit) § 5.7: the small line under the title ("AMC · Atlas Copco · SMTW") has its pattern
  in `frontend/src/views/masters/VendorsPanel.vue` now (`details(v)`: `[…].filter(Boolean).join(" · ")`
  in a `small text-secondary` div); name it beside `ManufacturersPanel.vue`.

## Checked and found consistent

- **The phone rule (§ 5.1, D11, A5).** `phone_parser(label)` exists in `backend/masters_core.py`
  with `_parse_phone = phone_parser("Phone")`, `PHONE_MAX = 20`, `PHONE_DIGITS_MIN = 6`,
  `PHONE_DIGITS_MAX = 15`, `PHONE_RE = ^\+?[0-9 ().-]*$`; `None` or `""` → `None`; messages
  "<label> must be text", "<label> must be at most 20 characters", and `PHONE_RULE` "Enter 6 to 15
  digits. Spaces, hyphens, dots and brackets are allowed." Each § 8.2 example behaves as the brief
  says: "+91 00000 00000" and "(044) 0000-0000" pass; "call 000000" and "00000" give `PHONE_RULE`;
  21 characters give the length message; "" → `None`. Nothing of S079's is renamed.
- **The masters_core helpers to alias (§ 3, D9).** `_collapsed`, `_flag_parser` (true/false/1/0),
  `_validate(data, fields, creating)` (an absent field is skipped unless creating and required),
  `_parse_id(label)` (→ `_choose_text`, "Choose a site.") and the public `optional_text_parser` all
  exist with the behaviour § 5.1 states.
- **The store (§ 3, A1).** `vendors` ref, `ensureVendors({ refresh })`, `fetchItems` with
  `?include_inactive=1`, cleared in `resetMasters`.
- **The vendors route (§ 3, § 5.7, A1).** `GET /api/masters/vendors`, key `masters:read` (`("*",)`,
  so every Contracts user holds it), `_include_inactive()`, answer `{items, total}` with items
  `{id, name, phone?, note, active, people_count, created_*, updated_*}` (`phone` only for
  `equipment:edit`). `PUT /api/masters/vendors/<id>` needs `equipment:edit`, which the engineer
  holds, so § 3's "an inactive vendor: a `PUT {active: false}` as the engineer" works.
- **The fixture (§ 3, § 8.2).** `make_vendor(**overrides)` posts `{"name": uniq.vendor_name(), …}` as
  `admin` to `/api/masters/vendors`, asserts 201 and returns the JSON. `_TABLES` holds `vendors` after
  `people`; `contracts` first in the tuple is right.
- **The migrations (§ 3, § 4.1).** v42 is the last entry of `_MIGRATIONS` (`LATEST_VERSION` 42, so
  43 after S080); `vendors (id INT AUTO_INCREMENT PRIMARY KEY, name, phone, note, active, created_*,
  updated_*)` exists for `fk_contracts_vendor`; no `ON DELETE` clause anywhere in v42, as § 4.1 says of
  the schema. No `_PRECONDITIONS` entry for v42, so § 4.1's "runs first in the same upgrade" holds.
- **The Masters tab order (§ 5.7, D12).** Sections now end "… Trades, Vendors, Team"; *Contracts*
  after *Team* is still last, and D12's "S079 puts *Vendors* there [before *Team*]" is right.
  `frontend/e2e/masters.spec.js` (the section loop and the four S079 tests) clicks sections with
  `exact: true`; a *Contracts* button clashes with none. `frontend/tests/masters.test.js` tests the
  store, not the section list.
- **The lock notes (§ 5.6).** `masters.py`'s docstring: "a vendor update locks its row alone and
  counts nothing. A person write that newly links a vendor locks the person, then reads the vendor
  LOCK IN SHARE MODE (person → vendor → trades); no vendor write takes a person, so no cycle"; the
  Team block: "person -> vendor (share, a new link only) -> trades -> site rows -> units".
  `update_vendor` takes `_lock_row(cur, "vendors", id)` and nothing after it. The brief's three
  bullets about S079 hold; no cycle with a contract write.
- **The docs the brief cites.** `docs/Plan.MD:48` (§ 2 item 9) and `:218` (`procedure:edit`) are
  still those lines after S079's Plan edits. `.claude/CLAUDE.md` *Self-check, repo items* (2) is
  unchanged (S079 added only the § SMTW-Review point *Vendor link (S079)*, after which S080's point
  goes). `backend/config_rbac.py` was not touched by S079.

## Feedback

- none
