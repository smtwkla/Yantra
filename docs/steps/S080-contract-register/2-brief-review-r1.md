```
Step: S080 — Contract register
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R02.1
```

Reviewed against: d216f48 (no uncommitted code; the uncommitted changes are the R02 docs, `docs/Plan.MD`
and the two step folders. S079 is not coded yet: every name marked "from S079" was checked against
`docs/steps/S079-vendor-master/1-brief.md`, not code.)

# S080 — Brief review, round 1

**Verdict: no `blocker` or `major` finding is open.** Five `minor` findings and seven nits. The design
is sound: the rules sit in `contracts_core`, the shell is thin, the gated fields have one builder and
one write filter, the lock order adds no cycle, and the two briefs (S079, S080) agree on the vendor
table, the route, the fixture and the phone rule. The facts file `scratch/brief-facts-S080.md` was
given and used; every cited line and name it lists is right at HEAD (`SITE_SCOPED` is at :197 as the
brief says in § 5.5, and :150 in § 3 is the comment line above `procedure:edit`, which is what the
brief means).

**Two points need KLA's own decision** (the brief lists them as § 9 Q1 and Q2; nothing in this
review changes them, but gate A is delegated tonight, so they are marked here):

- **KLA — Q2, IT admin and the call-out number.** As written (D5, D10 "engineers, managers and
  admin"), IT admin may add and edit a contract but never sees or enters the call-out number or the
  cost note. In practice the engineer must enter the number after IT admin's save. The brief follows
  the roadmap; the alternative is `contract:read` for IT admin too (one tuple change, one role-matrix
  row). Fact: the brief's reading of D10 is consistent with Plan.MD § 2 item 9 ("engineers, managers
  and admin; `contract:read`"), where "admin" is the realm admin. **Recommendation:** keep the brief
  (least privilege, ISO 27001 A.8.2) unless KLA wants IT admin to be able to type the number.
- **KLA — Q1, no cost column in the list.** Mock-up 01 shows *Cost (₹)*; D8 moved the price to R02.2's
  machine rows, so the brief shows no cost in S080. **Recommendation:** the brief's choice (a); the
  total comes with S081.

## Findings

### BR1-01 — minor — § 5.1 names messages the parsers it reuses cannot produce; one style is needed

**Problem.** § 3 and D9 say the text fields use `masters_core.optional_text_parser`. That parser's
texts are fixed: "`<Label> must be text`" and "`<Label> must be at most <n> characters`"
(`backend/masters_core.py:111-125`). The § 5.1 table instead gives "Covered: up to 1000 characters.",
"Notes: up to 1000 characters.", "Cost note: up to 255 characters.", "Contract number: up to 60
characters." (the form of `procedures_core.TITLE_TOO_LONG`, which has no trailing period), beside
"Call-out number must be at most 20 characters" (S079's phone rule, the masters' form). So the one
dialog would show two length-message styles, and the coder cannot satisfy both the reuse claim and the
table.

**Why it matters.** CLAUDE-COMMON scope B: the same kind of message reads the same everywhere in the
app. The coder must choose alone otherwise.

**Options.**
- (a) **Recommended.** Keep the brief's texts for *missing* fields ("Enter a title.", "Choose a
  site.", the S064 UX-13 form that `_choose_text` already uses) and for *too long* use the parsers'
  own form, "`Title must be at most 100 characters`", by reusing `optional_text_parser` (and
  `_parse_bounded_name`'s form for the title). One style with the call-out number's messages; the
  § 5.1 table and § 8.2's expected texts change to match.
- (b) Keep the "`<Label>: up to <n> characters.`" texts and write a small text parser in
  `contracts_core` with them (as `procedures_core` does); drop the `optional_text_parser` reuse from
  § 3 and D9. The phone message then stays the odd one out unless S079 changes its wording too.

Either way, settle the trailing period: `_choose_text` and the brief have one, `procedures_core` has
none.

### BR1-02 — minor — § 5.7 names *Set inactive* / *Set active*; `ActiveToggle.vue` says *Deactivate* / *Reactivate*

**Problem.** § 5.7 item 14 and *Destructive control* describe the footer control as *Set inactive* /
*Set active* with the confirmation "Set Atlas Copco AMC 2026–27 inactive? It leaves the list; Show
inactive brings it back." The shared component (`frontend/src/components/ActiveToggle.vue`, used by 17
files) renders *Deactivate* / *Reactivate* and "Deactivate **<label>**? Yes / No"; the words live in
the component, not in the panel. Every masters browser test clicks `"Deactivate"`.

**Why it matters.** Same word for the same action across the app (scope B). A coder following the
brief would either change the shared component (a change the brief says it does not make) or write a
second toggle.

**Options.**
- (a) **Recommended.** Use `ActiveToggle` as it is; the brief's text becomes *Deactivate* /
  *Reactivate* and the component's own confirmation. § 1 item 4 and § 5.3 may keep "set inactive" as
  prose for the state; the control's words are the component's.
- (b) Change `ActiveToggle`'s texts for every master (a shared change: the whole browser suite runs
  again). Not for this step.

### BR1-03 — minor — the field loop, the id parser and the date helper are planned as copies

**Problem.** § 3 says `contracts_core` imports from `masters_core` "only public names:
`optional_text_parser` and the two new aliases `collapsed`, `flag_parser`". `validate_contract` then
needs a field loop with the create/update rule (that is `masters_core._validate`, 12 lines), an id
parser that says "Choose a site." (that is `_parse_id` with `_choose_text`), and a `YYYY-MM-DD` parser
(the brief points at `improvements_core._iso_date`, private, 7 lines). None of the three is named as
reused or as a stated copy.

**Why it matters.** DRY (CLAUDE-COMMON § Engineering rules); and D9's own reason — "one copy of each
rule, no private import" — applies to the loop and the id parser as much as to `collapsed`.

**Options.**
- (a) **Recommended.** Add two more public aliases beside D9's: `validate_fields = _validate` and
  `id_parser = _parse_id` (so "Choose a site." and "Choose a vendor." come from `_choose_text`, and
  the required-on-create rule from one place). The date helper: a stated 7-line copy in
  `contracts_core` is acceptable (two cores should not import each other for it); say so in § 3.
- (b) Write the loop in `contracts_core` as `procedures_core` and `improvements_core` do (the newer
  cores have their own), and say so in § 3 and D9. Acceptable, but then the brief's reuse claim should
  shrink to the two text/flag parsers.

Note for (a): `_missing_text("title")` gives "Title is required", not the brief's "Enter a title."; the
choice of BR1-01 decides which, and the § 5.1 table follows.

### BR1-04 — minor — the phone factory belongs in S079, not as an S080 rename of S079's code

**Problem.** D11 and § 3 have S080 turn S079's `_parse_phone` into `phone_parser(label)` and keep
`_parse_phone = phone_parser("Phone")`. Both briefs are in review tonight and S079 is coded first, so
S080 plans to rename code that does not exist yet; S079 § 3 and § 5.1 define `_parse_phone` directly.
The two briefs agree on the rule (20 characters, `^\+?[0-9]+([ -]+[0-9]+)*$`, 6–15 digits, S079's
three messages), only on the shape of the function.

**Why it matters.** A rename across steps costs a staleness check, a second edit of `masters_core.py`
and of `test_masters_core.py`, for a function S079 can write in its final form in one line.

**Options.**
- (a) **Recommended.** S079 defines `phone_parser(label)` and `_parse_phone = phone_parser("Phone")`
  (the orchestrator carries one line into S079's brief or Review log); S080's `masters_core.py` change
  shrinks to the two aliases of D9, and § 8.2's `test_masters_core.py` case becomes
  `phone_parser("Call-out number")` only.
- (b) Keep the rename in S080 as written; the staleness review before S080's coding checks it (the
  brief's A5 already says so).

### BR1-05 — minor — on a phone the table hides the site, so a manager of two sites cannot tell the rows apart

**Problem.** § 5.7's table hides *Site* below `md` (`d-none d-md-table-cell`) and shows type and vendor
under the title. A manager who holds both sites (the e2e manager; Toyota MH has a contract per
company, Q1.5) sees two rows "Toyota MH AMC 2026–27 · Toyota Material Handling" with nothing to say
which is SMTW's, unless the Site filter is set or the title names the site, which nothing enforces.

**Why it matters.** The row must carry what the person scanning it needs (reviewer's UX list: "what a
row shows, as the person scanning it needs it"). Smaller friction, so `minor`.

**Options.**
- (a) **Recommended.** On a phone, show the site code in the small line under the title with the type
  and vendor ("AMC · Atlas Copco · SMTW"), for every user (one layout, no per-role branch); the
  `@device` test of § 8.4 asserts it.
- (b) Show it only when `sites` has more than one entry. Saves a few characters for a one-site user;
  one more branch.
- (c) Leave as is and rely on the Site filter.

## Nits

- **BR1-06** (nit) § 8.2, the 200-cap test: `contracts.py` imports `MAX_PER_PAGE` by name, so the test
  must patch `contracts.MAX_PER_PAGE`, not `api_common.MAX_PER_PAGE` (no existing test patches it; say
  which).
- **BR1-07** (nit) § 5.5: `grantable_site_ids` is a method of the people viewer class in
  `backend/masters.py:1143`, not a module function; write "as the Team viewer's `grantable_site_ids`
  does".
- **BR1-08** (nit) § 5.7 item 10, the help text "Tick when the contract ends if anyone else repairs the
  machine." — "ends" reads as the To date; write "Tick when the contract is void if anyone else repairs
  the machine. The machine's page will then warn: Do not repair." (scope B).
- **BR1-09** (nit) § 5.7 item 2, the type label "Warranty — the maker's" is a fragment; "Warranty — the
  maker's guarantee" (scope B, one idea per label).
- **BR1-10** (nit) § 8.4, the test title "the engineer sees no Edit on another site's contract" — the
  test asserts the BRICKS row is absent from the engineer's list (no `contract:read_basic` at BRICKS),
  not an *Edit* button missing; title it "does not see another site's contract; the manager sees Edit
  on both".
- **BR1-11** (nit) § 5.3 *Order*: with `status=all`, ascending `to_date` puts every ended contract
  above the live ones; say that it is accepted (the default view is `not_ended`), or sort `all` as
  `ended` last.
- **BR1-12** (nit) `docs/steps/INDEX.md:89` still says `Draft` while the brief's header says `In
  review` (README § Gates: whoever changes the status updates the row).

## Checked and found consistent

- **The two briefs agree:** `vendors` (S079 § 4.1: id, name, phone, note, active, who/when; migration
  v42, S080's v43 follows); the route `GET /api/masters/vendors` with `include_inactive=1`
  (`masters:read`); the store's `vendors` / `ensureVendors`; the fixture `make_vendor(admin, uniq)`;
  S079 § 5.1's rule "a vendor can be deactivated with links; from R02.1 on an inactive vendor is not
  offered for a new contract; a contract keeps its vendor" is exactly S080 § 5.2; the phone rule's
  pattern, bounds and three messages (BR1-04 is only about the function's shape). S079's *Vendors*
  tab goes before *Team*, S080's *Contracts* last: no collision in `MastersView.vue`.
- **Roadmap:** every R02.1 field, key, badge text and screen text (§ R02.1 *Text on screen*) is in the
  brief; D5, D7–D11 and Q1.1, Q1.3 a, Q1.4 b, Q1.5 a, Q1.8 a are followed; D8's "R02.1 holds the cost
  note only" is honoured (Q1 above). `renewal_of_id` created empty for R02.4 as the roadmap asks.
- **RBAC:** the four keys with the stated holders give exactly the `test_role_matrix` changes § 8.3
  lists (`ROLE_INCLUDES`: manager ⊇ engineer; `("*",)` reaches every role in `ROLES`, the storekeeper
  and IT admin included, not `maintenance_team`: `access_core.compute_permissions:58`). `has_perm_at`
  asserts the key is in `SITE_SCOPED` (`auth_utils.py:435`), which the brief adds. IT admin's token
  role holds `contract:read_basic` and `contract:edit` at every site (`access_core.permissions_at`).
  `require_perm` → 403 when held nowhere; `require_perm_at` → "You can't do this at <code>" with the
  field (`auth_utils.py:451-463`). `test_site_scoped_keys_exist` stays green.
- **Layers:** status, bounds, validation and filter dates in the pure core; `today` passed in by the
  shell; one `_contract_out` for every answer and one write filter (D4). `IST` imported from
  `equipment.py` as `improvements.py:181` and `meters.py:49` do.
- **Locks:** the sequence of § 5.6 against `equipment.py`'s LOCK ORDER note, `masters.py`'s docstring
  and S079 § 5.3. `masters.py` locks sites and never a vendor or a contract; S079's vendor update
  locks its own row only; the contract row is locked only by `contracts.py`'s `PUT`, first. No cycle.
- **Migration:** `CREATE TABLE IF NOT EXISTS`, `ENUM` as `people.employment` and `equipment.level`
  use, foreign keys `RESTRICT` as the schema's, no `_PRECONDITIONS` entry (a new table; the entries
  guard v20, v25, v34 only, `local_db.py:1478`). `test_migration_v41.py` slices `range(20, 42)`, so the
  v43 pattern (`range(20, 44)`, `_keys` / `_foreign_keys` from `test_migration_v36`) is right.
  `LATEST_VERSION = _MIGRATIONS[-1][0]`, so `test_modules.py` follows.
- **Existing tests:** the Masters section loop and every section click in `masters.spec.js` use
  `exact: true` with the section name; `screens.spec.js` waits for `"Sites"`; `frontend/tests/
  masters.test.js` tests the store, not the section list; `conftest._TABLES` is deleted with
  `FOREIGN_KEY_CHECKS = 0`, so `contracts` first is for reading only, as stated.
- **e2e seed:** the engineer holds SMTW only, the manager SMTW and BRICKS, IT admin a token role
  (`tooling/e2e/seed_e2e.py:42-51`), as § 8.4's per-site test needs. The new spec keeps its helpers
  out of `e2e/support/`, so no WebKit run is due.
- **Dialog on a phone:** `FormModal` is `modal-dialog-scrollable modal-fullscreen-sm-down`
  (`FormModal.vue:167`), so the 14 fields scroll with Save always visible; the one-tap path (vendor,
  title, two dates with one site and the default type) is right for an engineer at shift end;
  destructive control behind `ActiveToggle`'s confirm; no control shown without its right (S070 D10).
- **Standards:** the clauses named match their standards: ISO 55001:2014 § 8.3 *Outsourcing*;
  ISO 9001:2015 § 8.4 *Control of externally provided processes, products and services* (8.4.3
  *Information for external providers*) and § 7.5 *Documented information*; EN 13269 *Maintenance —
  Guideline on preparation of maintenance contracts*; ISO/IEC 27001:2022 A.5.15 *Access control* and
  A.8.3 *Information access restriction*. Each is explained in plain words and the departure (no value
  history) is recorded, as the settings ask.
- **Manual checks:** every check is a browser test; none is put on the device list; the `@device`
  tag is on the one layout test only. **Track full** is right (a migration, four keys, locks).
- **Facts file:** `scratch/brief-facts-S080.md` given; every "not found" name is either new in S080
  or marked "(from S079)".

## Feedback

- idea: the facts file marks S079's names as "planned in S079" but gives no definition, so checking
  that the two briefs agree meant reading S079's 584-line brief whole (about 10 minutes); a facts
  section that quotes the lines of the other open brief where each "(from S0NN)" name is defined
  would cut that to the lines that matter.
- hindrance: the brief cites UI words that live in a shared component (`ActiveToggle.vue`), and the
  facts file's *Screen text in the tests* lists only labels written as `"Label"` in the brief, so the
  *Set inactive* / *Deactivate* mismatch (BR1-02) needed a read of the component; a facts entry for
  each `*Italic*` control name the brief uses, with the file that renders it, would show it at once.
- rule: README § Header block gives no form for a `Baseline:` of a brief planned ahead of the step it
  depends on; this brief writes "S079 (vendors, v42) coded before S080" in free text, which the stale
  brief check will have to read by hand.
