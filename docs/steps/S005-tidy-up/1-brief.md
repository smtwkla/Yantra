```
Step: S005 — Tidy-up: page not found, leftover review nits
Doc: brief
Author: Planner (Opus)
Date: 15-10-2026 (revised 15-10-2026 after brief-reviews r1 and r2)
Status: In review
```

# S005 — Tidy-up: page not found, leftover review nits

A small step before real users arrive: a proper "page not found" page, and the
code nits left open by S002, S003 and S004 code reviews.

**Depends on:** S004 committed. Two of the nits are in S004's code.

Background reading:
- `docs/steps/S002-equipment-register/4-code-review-r2.md` (CR2-02);
- `docs/steps/S003-equipment-screens/4-code-review-r2.md` (CR2-01);
- `docs/steps/S004-equipment-types-notes/4-code-review-r1.md` (CR1-01, CR1-02);
- `.claude/SMTW-WebApp-Base.md` § Frontend Design.

## 1. What will be built

1. **A "page not found" page.** Today an address that matches no route (a typo,
   an old bookmark, `/equipment/abc`) shows an empty content area with no
   message, and Vue Router logs a warning. Instead the user sees "Page not found"
   and a button to their landing page.
2. **Four leftover nits**, each a few lines:

   | From | Nit | Change |
   |---|---|---|
   | S002 CR2-02 | After a save has **committed**, the response read can answer 409 "This record changed while saving — try again". Unreachable today, but a retry of a create would make a duplicate | The post-commit reads use a message that doesn't invite a retry (§ 4.2) |
   | S003 CR2-01 | The 300 ms search delay is defined in two files | One `SEARCH_DELAY_MS` exported by `useDebounced.js`, the default of `useDebounced` (§ 4.3) |
   | S004 CR1-01 | The `_lock_type` docstring describes a case that can't happen | Reworded (§ 4.4) |
   | S004 CR1-02 | A hand-made URL with a class and a type of another class shows a blank Type filter while the filter still applies | The URL's type is listed in the filter, labelled `CLS · Name` (§ 4.5) |

**Out of scope:**
- Wording corrections in Done steps' reports (S002 CR2-01, S003 CR1-03). Those
  files are the record of what was reported at the time; they stay as written.
  This brief notes the corrections (§ 6).
- S003 CR1-08 (unit tests for the list's URL rules): declined by the user at
  S003 gate B.
- Findings the user rejected in S001 (CR1-09, CR2-01).
- A "not found" answer for unknown **API** paths (`/api/nope`). That is backend
  error handling and isn't needed for users.
- Any other change.

## 2. Standards and practice

No maintenance standard applies; this is software hygiene.
- **Usability (ISO 9241-110:2020, interaction principles "self-descriptiveness"
  and "use error robustness").** ISO 9241-110 lists the principles a usable
  dialogue follows; two apply here: the screen should explain itself, and a
  user's mistake (a mistyped address) should be easy to recover from. So the
  page names the problem and offers one way out, instead of a blank area.
- **ISO 27001:2022 A.8.28 (secure coding).** The page echoes the address the user
  typed, so it is rendered as text (`{{ }}`), never as HTML (`v-html`).
- **CLAUDE-COMMON DRY:** one search delay, defined once.

## 3. Where

### Frontend

- **`frontend/src/views/NotFoundView.vue`** (new): the page (§ 4.1).
- **`frontend/src/stores/navigation.js`:** `landingNavItem(permissions)` returns the
  first nav item the user may see, or `null`; `landingPath` becomes
  `landingNavItem(...)?.path ?? null`, so the rule stays in one place (BR1-03).
- **`frontend/src/router/index.js`:** a last route
  `{ path: "/:pathMatch(.*)*", name: "not-found", component: NotFoundView, meta: { title: "Page not found" } }`.
- **`frontend/src/composables/useDebounced.js`:** `export const SEARCH_DELAY_MS = 300`;
  `useDebounced(callback, delayMs = SEARCH_DELAY_MS)`.
- **`frontend/src/views/EquipmentView.vue`** and
  **`frontend/src/views/equipment/EquipmentMoveModal.vue`:** drop their local
  `SEARCH_DELAY_MS` and the second argument.
- **`frontend/src/views/EquipmentView.vue`:** the Type filter fix (§ 4.5); the
  comment that says "300 ms after the last keystroke" names
  `SEARCH_DELAY_MS` instead, so the number appears only once (BR1-06).
- **`frontend/tests/navigation.test.js`:** `canOpenRoute("not-found", …)` is
  `true` for every role, including none; `landingNavItem` returns the Equipment
  item for every role and `null` for none.

### Backend

- **`backend/equipment.py`:**
  - the post-commit response reads (create and PUT) pass a message that doesn't
    invite a retry (§ 4.2);
  - the `_lock_type` docstring (§ 4.4).
- **`backend/tests/test_equipment_api.py`:** a test of § 4.2 on create, with the
  existing `stale_reread` fixture: its change returns the row on the first call
  (the in-transaction read) and `None` on the second (the post-commit read). It
  asserts 409 with the new message **and** that the equipment was saved (it is
  in the unit's list, and the next code of the class is `+2`): the mirror of
  S002's rollback test, which asserts `[]` and `+1` (BR1-02, BR2-03).

### Docs

None for the coder.

## 4. Rules

### 4.1 Page not found

- **Matches** any path no other route matches. Routes are matched in the order
  given, and the catch-all is last, so every existing route wins.
- **Shows**, in the content area (sidebar and topbar stay):
  - an icon and the heading "Page not found";
  - "The address **/the/path** doesn't exist in Yantra.", with `route.fullPath`
    (query string included), rendered as text and allowed to wrap (BR1-07);
  - a button to the user's **landing page** (`landingNavItem(userPermissions)`:
    its path and label),
    labelled "Go to <nav label>", e.g. "Go to Equipment". With no landing page
    (no permissions), the button is hidden.
- **The router guard** lets it through: it is not a nav item, so `canOpenRoute`
  already allows it. Before login completes nothing renders, as today.
- **The sidebar** highlights by path prefix, as today (S003): on `/equipment/abc`
  Equipment stays highlighted, on `/nope` nothing. That is accepted: the user is
  still "in" that area (BR1-01).
- **Not used for API 404s.** The equipment page keeps its own "Equipment not
  found, or not at your units" message (S003 § 4.2), because there the address
  is valid and the record is what's missing.
- **No server change.** In production Nginx already sends every unknown path to
  `index.html` (SPA fallback: `tooling/build/nginx.conf`, shipped by
  `Dockerfile.frontend`; verified at review), so the router decides.

### 4.2 Post-commit read message (S002 CR2-02)

- `_reread(cur, node_id, message=…, field=None)` already takes a message.
- The two **post-commit** calls (after `transaction()` has committed, in
  `create_equipment` and `update_equipment`) pass:
  "Saved, but the record could not be read back — reload the page", status 409
  as today.
- Inside the transaction nothing changes: there "try again" is right, because
  the transaction rolls back.
- A one-line comment at each post-commit call says why the message differs.

### 4.3 One search delay (S003 CR2-01)

- `useDebounced.js` exports `SEARCH_DELAY_MS = 300` and uses it as the default
  delay.
- The two callers stop defining their own and call `useDebounced(fn)`.

### 4.4 `_lock_type` docstring (S004 CR1-01)

Replace "An inactive type may be kept (a class change keeping it) but not newly
chosen" with: "The active check applies only when this write chooses the type; a
type kept from before is checked for its class only (and keeping a type without
a class change takes no lock at all)."

### 4.5 Type filter with a type of another class (S004 CR1-02)

- When the URL's `type_id` isn't among the chosen class's types, the Type filter
  also lists that type, **last**, so the applied filter is always visible. The
  label rule: `CLS · Name` whenever the type's class isn't the chosen class (so
  also when only `type_id` is in the URL), the plain name otherwise (BR2-02).
- A `type_id` that matches **no** type (`?type_id=999999`) is left as is: the
  select stays blank and the list is empty, the same as the class filter does
  with an unknown `class_id` (BR1-04).
- Nothing else changes: choosing a class still clears the type.

## 5. Tests and acceptance

- **Frontend (vitest):** `navigation.test.js`, `canOpenRoute("not-found")` for
  every role and for `[]`; `landingNavItem` returns the Equipment item for every
  role and `null` for `[]` (BR2-01).
- **Backend:** § 3.
- **Manual (user):**
  - `/nope`, `/equipment/abc`, `/masters/x`: "Page not found" with the path,
    the button "Go to Equipment" goes there; the sidebar and topbar stay;
  - `/equipment/999999`: still "Equipment not found, or not at your units";
  - both search boxes still wait before searching;
  - `/equipment?class_id=<RPP>&type_id=<a type of another class>`: the Type
    filter shows that type, and the empty list makes sense.
- **Acceptance:** `tooling/run-tests.bat` green; `npx vite build` clean.

## 6. Notes on Done steps' reports (not changed)

For a later reader of the S002 and S003 reports:
- **S002 `3-impl-report.md`, round-1 residuals (CR2-01):** the "site rename"
  case can't happen (a site with units can't be renamed). The open case is an
  empty target unit moved to another site while an equipment move waits for its
  lock. In the grandparent case, the unit and site codes of the path can be
  stale too. Both remain display-only.
- **S003 `3-impl-report.md` (CR1-03):** the backend count before S003 was 448,
  not 436; S003 added 14.

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| A catch-all route with its own page | The user is told what happened and gets a way back | Redirecting silently to the landing page (hides typos and stale bookmarks) |
| The button goes to the user's landing page | One rule (`landingNavItem`, which `landingPath` also uses) for "home" | A fixed "/equipment" |
| Done steps' reports aren't edited; corrections noted here | They record what was reported at the time | Editing old reports |
| The post-commit message says "reload", not "try again" | A retry after a committed create would duplicate | Only a docstring note |

## 8. Open questions and assumptions

1. **Assumption:** the coder is Sonnet: UI and a few one-line backend changes,
   no locking or schema change.
2. **Checked (review r1):** production Nginx has the SPA fallback (§ 4.1).

## 9. (not used)

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 15-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 The sidebar does highlight on `/equipment/abc` | major | **Accepted, option (a).** The prefix highlight is accepted and stated; no code (§ 4.1). |
| BR1-02 The post-commit test is decidable | minor | **Accepted.** A two-call `stale_reread` test on create, asserting 409 and that the write persisted (§ 3). |
| BR1-03 The button label needs the nav item | minor | **Accepted.** `landingNavItem`, with `landingPath` derived from it; tested (§ 3). |
| BR1-04 Where the foreign type sits; unknown type | minor | **Accepted.** Listed last; an unknown id left blank, like the class filter (§ 4.5). |
| BR1-05 ISO 9241-110 term; echoed path as text | nit | **Accepted.** "Use error robustness" (2020); A.8.28, no `v-html` (§ 2). |
| BR1-06 The comment still says 300 ms | nit | **Accepted** (§ 3). |
| BR1-07 Show `route.fullPath`, wrapping | nit | **Accepted** (§ 4.1). |
| BR1-08 Amendments numbering | nit | **Accepted.** Amendments is § 10 (§ 9 unused). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 15-10-2026

All eight round-1 answers verified; the BR1-02 test design checked against the
fixture and the call sites. No blocker or major finding.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 § 4.1 and § 7 still name `landingPath`; § 5 lacks the tests | nit | **Accepted.** Both name `landingNavItem`; tests in § 5. |
| BR2-02 The foreign type's label rule | nit | **Accepted.** `CLS · Name` whenever the type's class isn't the chosen class (§ 4.5). |
| BR2-03 What "saved" means in the test | nit | **Accepted.** In the unit's list, next code `+2` (§ 3). |
