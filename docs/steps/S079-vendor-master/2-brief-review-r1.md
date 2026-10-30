```
Step: S079 — Vendor master
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R02.9
```

Reviewed against: d216f48 (uncommitted changes are the R02 re-plan docs only: `docs/Plan.MD`, `docs/roadmap/*`, `docs/steps/INDEX.md`; no code)

# S079 — Brief review, round 1

**Verdict: no blocker or major finding is open.** Three `minor` findings and seven nits. The brief
is accurate about the code it touches: every file, name, lock note, permission tuple and test
anchor I checked holds. Facts file used: `scratch/brief-facts-S079.md`.

**For KLA's own decision** (gate A delegated tonight; these are the brief's own questions, not
defects): § 9 Q1 (who reads the vendor's phone), Q2 (one row for Toyota Material Handling) and
Q3 (the SMTW-Review point). Each has a sound recommendation; none changes the design if taken as
recommended. BR1-01 below is a judgement call too; the orchestrator may take it under the
delegation, or leave it to KLA.

## Findings

### BR1-01 — minor — § 5.1: the phone pattern refuses what people copy from a letterhead

**Problem.** The rule `^\+?[0-9]+([ -]+[0-9]+)*$` refuses parentheses and dots, so
`(044) 2345 6789` and `044.2345.6789`, both common on Indian letterheads and websites, come back
with the message "Enter 6 to 15 digits. Use only digits, spaces, hyphens and a + at the start."
The engineer then has to retype the number in the app's shape. Three constants and a grouping
regex for one optional text field of ~10 rows is also more than the field needs
(CLAUDE-COMMON › Simplicity first; right-sized for ~50 users).

**Why it matters.** It is friction at the one moment a vendor is entered, and it buys little: the
number is shown as text and never dialled (D12). A junk value is already bounded by the 20
characters and the digit count.

**Options.**
- (a) **Keep the digit count, loosen the characters — recommended.** Trim and collapse spaces;
  at most 20 characters; 6 to 15 digits in total; every other character one of space, hyphen,
  parentheses or dot, with `+` allowed only first. Message: "Enter 6 to 15 digits. Spaces,
  hyphens, dots and brackets are allowed." Drop the grouping rule (`"00 00+"` is still refused
  by the `+` rule; `"-000000"` passes, which is harmless).
- (b) Keep the brief as written. Exact, and the examples are already in the tests.
- (c) Length only (20 characters), no pattern. Simplest; lets "call Ravi" through.

### BR1-02 — minor — § 5.5: the brief says the Deactivate confirm "states the consequence"; `ActiveToggle` does not

**Problem.** § 5.5 says the vendor dialog's *Deactivate* confirm "states the consequence through
`ActiveToggle`'s own text". `ActiveToggle.vue` shows only "Deactivate **<name>**? Yes / No"
(lines 34–38); it names no consequence. The coder reading the brief would expect a text that is
not there, or add one that no other master has.

**Why it matters.** Deactivating a vendor with linked people is the one place this step departs
from the manufacturer pattern (§ 2): the links stay, the vendor is no longer offered. The user
should know what happens, and the brief should say what the dialog really shows.

**Options.**
- (a) **Fix the brief's sentence; add no text — recommended.** Say the confirm is `ActiveToggle`'s
  plain "Deactivate <name>?", as every master; the action is reversible (*Reactivate*), and the
  linked people are listed right there in the *People* column. Add to § 5.5 one line under the
  *Deactivate* button when `people_count > 0`? No: keep the dialog as the others.
- (b) Add a small line beside the toggle while confirming, when `people_count > 0`: "Its <n>
  people stay linked; it is no longer offered for new links." One more branch in
  `VendorsPanel.vue` only; `ActiveToggle` unchanged.

### BR1-03 — minor — § 5.2 rule 2 / § 5.3: say where the vendor check sits among the person PUT's 403s

**Problem.** `update_person` today checks, in order: the locked row, the login save's sites, the
own-person 403s, the "only IT admin may (de)activate a person with a login" 403, then the trades
(400), the site rows, the update. § 5.3 lists the vendor steps as (2) the pure link check and
(3) the share-mode read, both right after `_lock_row`, i.e. before the two 403s. The brief does
not say whether that order is meant.

**Why it matters.** The module's stated rule for site rows is "400 before 403" (the Site roles
block comment), but the person PUT itself puts the own-person 403 before the trades' 400. The
coder has to choose; a test of "a refused link writes nothing else" passes either way, so the
choice would be silent.

**Options.**
- (a) **Place the vendor checks with the trades — recommended**: after the own-person and
  active 403s, before `_check_grantable`. The vendor is a grant like a trade, and the person's
  lock order (person → vendor → trades) is unchanged. One sentence in § 5.3's PUT line.
- (b) Keep them first (400 before 403, as the site-row rule). Also fine; then say so.

## Nits

- **BR1-04** (nit) § 5.2: `vendor_link_error(employment, vendor_id)` returns the text only and
  the shell picks the field (`vendor_id` when the body sends one, else `employment`). Return
  `(field, message)` or `None` from the pure function, so the whole rule is in one place and in
  `TestVendorLink` of `test_masters_core.py`.
- **BR1-05** (nit) § 5.5 Team dialog, the to-none warning: "If the person moved to another firm,
  add a new Team record for them instead." does not fit the *Direct employee* case (the person
  became an employee, not a firm's). One second sentence for both cases: "If the person changed
  firm or employer, add a new Team record for them instead."
- **BR1-06** (nit) § 9 "Fact": `06-vendors-tab.html` no longer says that no phone is kept; its
  note already reads "A vendor keeps an optional office phone, shown to engineers, managers and
  IT admin; no address (Q9.2, S079)." Drop the bullet.
- **BR1-07** (nit) § 3 Docs: "the Team text (line 163)" of `docs/Plan.MD` is a line anchor in an
  uncommitted file that S080 also edits; anchor by name (§ 2 item 9, § 3's Team paragraph), per
  README § Anchors by name.
- **BR1-08** (nit) § 8.4: name the allowed failed requests the new tests need, as the section
  loop does: the duplicate-name test `consoleWatch.allowFailedRequest("/api/masters/vendors", 409)`;
  the section-loop entry gets its 400 from the loop itself.
- **BR1-09** (nit) § 3 Tests: put `"vendors"` after `"people"` in `conftest._TABLES` whatever the
  FK setting, so the tuple reads children before parents like the rest of it.
- **BR1-10** (nit) § 5.5 phone help "The breakdown number goes on the contract.": there is no
  contract in the app until S080. Fine if S080 ships in the same release; otherwise "… goes on
  the contract (Masters › Contracts, coming)".

## Standards

Named and explained in plain words, as the settings ask: ISO 9001:2015 § 8.4 (control of
external providers: a list of providers is where the records start), ISO 55001 § 8.3
(outsourced work stays the plant's responsibility, so it must be traceable to the firm), ISO 14224
maintenance data (who did the work, in-house or contractor; this step adds the firm), ISO 8000
(one spelling per firm, the same rule as manufacturers), ISO/IEC 27001 A.5.15 / A.8.3 (the phone
to those who deal with the vendor). The departure from the manufacturer pattern (deactivate with
links) is stated with its reason. No TPM or EN 13306 point applies to a vendor master.

## Use on the floor

- The Vendors tab is one job (keep the firm list): name with phone and note under it, the
  People count, status, *Edit*. Nothing an engineer does not need; no search for ~10 rows.
- The Team dialog adds one select, shown only for a contractor, defaulting to *No vendor*; a
  save never meets rule 1's refusal from the dialog. The change warning sits in view above
  *Save person* (D11), no second confirm: right for a rare, reversible edit.
- Empty states are stated: the tab ("No vendors yet…"), the select ("No vendors yet; add one
  under Vendors."). Permission states: the tab and its buttons follow `canEdit`; every Masters
  viewer holds `equipment:edit` (verified: `navItems` perms are `masters:edit`, `equipment:edit`,
  `people:edit`, `failure_codes:edit`, all held by engineer/manager/IT admin; `ROLE_INCLUDES`
  gives the manager the engineer's keys), so the phone mask never shows on screen today.
- Messages are one or two short lines, no codes. The two warnings are the longest texts; BR1-05
  tunes one of them.

## Manual checks

Four automated checks, three marked **important**, all judgeable by a browser; the section-loop
entry covers the open-and-refuse check. No device check: correct, the phone field's keyboard is a
browser `inputmode` and no call is placed. Targeted specs and the whole-suite run are named; no
shared frontend file changes (verified: `FormModal.vue`, `useFormModal.js`, `api.js`, the router,
the auth store and `e2e/support/` are not in § 3).

## Checked and found consistent

- **Migration v42**: the `IF NOT EXISTS` forms match v35 and v41 (`ADD COLUMN`, `ADD KEY`,
  `ADD CONSTRAINT … FOREIGN KEY IF NOT EXISTS`, `ADD CONSTRAINT IF NOT EXISTS chk_…`).
  `people.employment` is `ENUM('direct','contractor')`, so the CHECK compares a stored value.
  `_PRECONDITIONS = {20, 25, 34}` as stated; none is needed. `test_migration_v41.py` slices
  `range(20, 42)` (lines 19–21), so v42 does not break it; `test_migration_v27.py` compares
  `SELECT * FROM people` at v27 only.
- **Shell and core**: `_parse_optional_id("Vendor")` gives exactly the brief's refusals
  (`true`, `"3"`, `0`, `-1`, `1.5` → "Vendor must be a record id"); `_parse_manufacturer_name`
  and `optional_text_parser` exist as cited; `_validate` ignores extra fields; `clean_body`
  answers "Request body must be a JSON object"; `update_row` does nothing on `{}`.
- **Permissions**: `equipment:edit` is `("maint_engineer", "it_admin")`, site-scoped;
  `has_perm` on it returns the union over sites (`access_core.global_permissions`), as the brief
  needs for `_vendor_out`; `people:edit` and `masters:read` as stated; supervisor and storekeeper
  do not inherit the engineer, so the `TestPhoneReaders` roles are right.
- **Locks**: the Team block's order (person → trades → memberships/person_units → units) is as
  the docstring says; `_check_grantable` locks trades `FOR UPDATE`; the share-mode read of the
  vendor after the person lock joins no cycle, since no vendor route takes a person row. The
  `_check_grantable` texts the brief copies ("That … no longer exists. Reload and try again.",
  "… is inactive. …") are the real ones.
- **Frontend**: `useMasterForm` passes `toBody` through to `useFormModal`; `afterSave` calls
  `resetMasters()` then `reload`; `fieldError`/`modalError` behave as § 5.5 assumes (a
  `vendor_id` refusal shows beside the select because `vendor_id` is in the form).
  `MastersView.sections` and `stores/masters.js` are as cited; `masters.test.js` has the "fetches
  each list from its own path, inactive included" case to extend.
- **Tests and fixtures**: `uniq` is session-scoped and `_clean_tables` empties `_TABLES` at
  session start, so `"Vendor 0001"` does not clash with leftovers once `vendors` joins `_TABLES`;
  `make_manufacturer(admin, uniq)` is the shape to copy; `role_client` and `db_down` exist.
- **e2e**: the section loop at `masters.spec.js:121–146` takes a `before` and a `message`;
  `openTeam`, `openPersonDialog` and `propertyTag` exist; no e2e test reads the Employment badge
  text or counts the Masters toolbar; `screens.spec.js` opens Masters by the *Sites* button only.
- **Docs**: Plan.MD § 2 item 9 already describes the vendors master (name, phone, note; optional
  link on a contractor's Team record); `notes.json` has no `vendors` entry (new) and its `people`
  line needs the column; Plant-Facts § 4 names Atlas Copco, Toyota Material Handling and
  Sartorius, and the roadmap (lines 31–33, 672–674) adds Fuji Electric and VP Power Systems from
  the contracts read 27-10-2026, so the five names are sourced. Mock-up 06 matches § 5.5.
- **Track**: full is right (a migration, locking, an API rule).

## Feedback

- idea: every permission claim in a brief needs the key's roles plus `ROLE_INCLUDES`; the facts
  file could print, for each `x:y` key the brief names, its tuple and the roles that inherit it
  (2 greps of `config_rbac.py` and a read of `auth_utils.has_perm` this round).
- waste: the facts file's *Files* entry reports a `.png` as "exists (5786 lines)"; a line count of
  a binary is noise (`docs/roadmap/R02-mockups/06-vendors-tab.png`).
