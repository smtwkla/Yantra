```
Step: S005 — Tidy-up: page not found, leftover review nits
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 15-10-2026
```

# S005 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01).** Three `minor` and four `nit`
findings. The brief is otherwise sound and proportionate: every claim it makes
about the code was checked against the working tree (S004 included) and holds,
except the sidebar claim in BR1-01.

Reviewed against: `1-brief.md`; the three code-review files it cites;
`frontend/src/router/index.js`, `stores/navigation.js`, `App.vue`,
`components/layout/AppSidebar.vue`, `AppBottomNav.vue`, `AppTopbar.vue`,
`composables/useDebounced.js`, `views/EquipmentView.vue`,
`views/equipment/EquipmentMoveModal.vue`, `tests/navigation.test.js`;
`backend/equipment.py` (`_reread`, `_written_state`, `_check_type_on_update`,
`_lock_type`, `create_equipment`, `update_equipment`),
`backend/tests/test_equipment_api.py` (`stale_reread`, `TestRereadAfterWrite`);
`tooling/build/nginx.conf` and `Dockerfile.frontend`; `SMTW-WebApp-Base.md`
§ Frontend Design; `CLAUDE.md`, `CLAUDE-COMMON.md`; `Plan.MD` (no decision touches
routing or a not-found page). Earlier rounds: none.

## Findings

### BR1-01 — major — § 4.1 "The sidebar highlights nothing on it" is not what the code will do

**Problem.** Both navs mark an item active with
`isActivePath(route.path, item.path)` (`AppSidebar.vue:32`, `AppBottomNav.vue:32`),
and `isActivePath` is a prefix match: `routePath.startsWith(`${itemPath}/`)`
(`navigation.js:37-39`). So on `/equipment/abc` Equipment is highlighted, and on
`/masters/x` Masters is — two of the three URLs in the brief's own manual list
(§ 5). Only `/nope` highlights nothing. S003's r2 review already observed this
("Equipment highlighted because `isActivePath` uses a prefix match"). The brief
lists no change to `navigation.js` or the two nav components, so the coder has
to choose between silently changing nav code and silently failing § 5.

**Why it matters.** A stated behaviour that the listed changes cannot produce is
exactly the "rule the coder decides alone" the step workflow exists to avoid,
and the bottom nav (mobile) is not mentioned at all.

**Options.**
1. **Accept the prefix highlight and delete the sentence.** Zero code. On
   `/equipment/abc` the user is "in" Equipment, which is a defensible reading,
   and the page itself says what went wrong. Keep § 5 as "the sidebar and topbar
   stay".
2. **Keep the intent and state the rule.** Highlight nothing when
   `route.name === "not-found"`. To keep one rule for both navs, put it in
   `navigation.js` rather than in each component, e.g. an `isActiveNav(route, item)`
   that both navs call, with `isActivePath` kept as it is so
   `navigation.test.js` ("an item stays active on its sub-pages") still passes;
   add one test for the not-found case. List the three files under § 3.

**Recommendation.** Option 1 (simplicity first; this is a tidy-up). If the user
prefers option 2, the brief must name the files and the test.

### BR1-02 — minor — § 3 leaves the backend test to the coder, but the question can be settled now

**Problem.** § 3 says: a test "with the existing `stale_reread` fixture, if it
can reach the post-commit read; otherwise none". Checked:
- as used today (`stale_reread(lambda row: None)`), it cannot: the first
  post-write read is `_written_state`'s `_reread` *inside* the transaction
  (`equipment.py:349`), which raises the old "try again" 409 before the
  post-commit read at `:482` / `:517` is reached;
- but the fixture takes any `change(row)` function, so a change that returns
  the real row on the first call and `None` on the second reaches the
  post-commit read without touching the fixture.

**Why it matters.** This test is the one that proves the wording decision in
§ 7: the message differs *because the write persisted*. Without it, nothing
pins that the "reload" message is used only after commit.

**Options.**
1. Prescribe the test: create (or PUT) with a two-call `change`; assert 409 with
   the new message, **and** that the write persisted — the node is in the list
   and the next code is `+1` — the mirror of
   `test_create_that_cannot_read_back_is_409_and_rolls_back`.
2. Drop the test and say so.

**Recommendation.** Option 1, one test on create (the duplicate-on-retry case
CR2-02 described). Remove the "if it can" conditional from § 3.

### BR1-03 — minor — § 4.1 the button label needs the nav item, but the brief only gives it the path

**Problem.** The button is "Go to <nav label>", but `landingPath(permissions)`
returns `"/equipment"`, not the item; nothing in `navigation.js` returns the
label. The coder has to either look the item up by path or add a helper, and
the brief should say which.

**Options.**
1. Add `landingNavItem(permissions)` to `navigation.js` (the item, or `null`)
   and make `landingPath` return `landingNavItem(permissions)?.path ?? null`.
   One rule for "home", as § 7 intends; the existing `landingPath` tests pass
   unchanged. The view uses the item's `label` and `path`.
2. In the view: `navItems.find((i) => i.path === landing)?.label`. No store
   change, but the lookup repeats the store's logic in reverse.

**Recommendation.** Option 1; add it to § 3 and one line to § 5 (`landingNavItem([])`
is `null`).

### BR1-04 — minor — § 4.5 two cases the coder would decide alone

**Problem.** The rule covers a `type_id` of another class. It does not say:
1. **where** the foreign type appears in the list (`typeChoices` is sorted
   active-first; the foreign one is an oddity, not a choice);
2. **what happens when `type_id` matches no type at all** (`?type_id=999999`):
   the select still shows blank while the list sends the filter — the same
   "filter applied invisibly" shape CR1-02 fixes, and the same thing the Class
   filter does today for `class_id=999999`.

**Recommendation.** State both: the foreign type is listed **last**, with the
usual "(inactive)" suffix when it applies; an unknown id is left as it is,
consistent with the class and unit filters (an explicit non-decision, so the
coder does not invent a placeholder option).

### BR1-05 — nit — § 2 standards: right standard, one outdated term

ISO 9241-110 ("Ergonomics of human-system interaction — Interaction principles")
is the right citation: it lists seven principles a dialogue should follow.
*Self-descriptiveness* means the user can always tell where they are and what
they can do next; the page's heading, the echoed path and the single button do
exactly that. The 2006 edition called the second principle *error tolerance*;
the current edition (2020) renamed it *use error robustness* — a use error
(here, a mistyped address) must leave the system in a state the user can
recover from with little effort. Cite the 2020 wording.

One security line is worth adding under this heading: the page echoes a
user-typed path. Vue's `{{ }}` interpolation renders it as text, so there is no
injection; the brief should say "as text, never `v-html`", which is the ISO 27001
secure-development control (A.8.28) in one phrase. Agree that no maintenance
standard applies: ISO 14224 / EN 13306 are about equipment data and maintenance
terms, which this step does not touch.

### BR1-06 — nit — § 4.3 the number would still be written in one more place

`EquipmentView.vue:120` has the section comment
`// ---- search: 300 ms after the last keystroke ----`. After the change this
comment is the only remaining copy of the number and will drift the first time
`SEARCH_DELAY_MS` is tuned. Reword to "after the last keystroke
(`SEARCH_DELAY_MS`)" and have the `useDebounced` JSDoc name the default.

### BR1-07 — nit — § 4.1 "the path as typed": say which property, and let it wrap

With `/:pathMatch(.*)*` the param is an array; the page should show
`route.fullPath` (so `/nope?x=1` shows the query the user typed, which is what
"as typed" means) rather than the param. A long pasted path should wrap
(`text-break`), not push the content area sideways.

### BR1-08 — nit — Amendments is § 9; the README and every other brief have it as § 10

README § Amendments says "under the brief's **§ 10 Amendments**", and S001, S003
and S004 number it so (§ 9 Open questions, § 10 Amendments). S005 has § 8 Open
questions, § 9 Amendments. Harmless, but the README reference is literal;
either renumber or leave a note.

## Checked and found consistent

- **The four nits are described accurately.** CR2-02 (`_reread` at
  `equipment.py:482` and `:517`, after `transaction()` has exited; the
  connection is autocommit, `local_db.py:200`, so the path is indeed unreachable
  today); CR2-01 (`SEARCH_DELAY_MS = 300` at `EquipmentView.vue:25` and
  `EquipmentMoveModal.vue:18`; `useDebounced(callback, delayMs)` has no default);
  CR1-01 (`_lock_type` docstring at `:277-278`); CR1-02 (`typeChoices` at `:79-83`
  filters by `class_id` and `typeLabel` at `:84` switches on `class_id`).
- **§ 4.4 replacement wording is correct** against `_check_type_on_update`
  (`:305-316`): no lock when the type is kept and the class is unchanged
  (`:313`); the active check only when `"type_id" in clean` (`:316`); the class
  check always. The first sentence of the docstring, with the lock number (5),
  is kept.
- **§ 4.2 keeps 409 after commit.** Acceptable: the path is unreachable, and the
  brief says so. Note for the record that `useFormModal` keeps the dialog open
  with Save enabled on any error, so the wording is the only guard against a
  duplicate — which is what CR2-02 asked for and no more.
- **The catch-all route.** `/:pathMatch(.*)*` is the Vue Router 4 form; placed
  last it cannot shadow `/equipment/:id(\d+)` or the trailing-slash matches
  (non-strict by default). The guard in `router/index.js:45-49` and the re-check
  in `App.vue:21-25` both go through `canOpenRoute`, which returns `true` for a
  name that is not a nav item, so no code change is needed there. The topbar
  shows `route.meta.title` (`AppTopbar.vue:17`), so "Page not found" appears as
  the page title. Before login, `App.vue` renders nothing (`v-if="authenticated"`).
- **Nginx SPA fallback: verified.** `tooling/build/nginx.conf:44`
  `try_files $uri $uri/ /index.html;` under `location /`, and
  `tooling/build/Dockerfile.frontend:14` copies that file into the container.
  There is no Nginx config under `frontend/`, so the brief should name
  `tooling/build/nginx.conf` for the coder. `/api/...` is proxied before the
  fallback, so an unknown API path still gets the backend's answer (out of
  scope, as the brief says); `/assets/...` has no fallback, which is right.
  Vite's dev server falls back to `index.html` by default.
- **Existing tests.** `navigation.test.js` already has
  `canOpenRoute("not-a-nav-item", OPERATOR)`; the new `not-found` cases are a
  sharper version of it and break nothing. No test breaks on `useDebounced`
  gaining a default. The backend's `RETRY` message constant in
  `TestRereadAfterWrite` stays correct: those tests hit the in-transaction read.
- **Out of scope list** matches the record: S002 CR2-01 and S003 CR1-03 are
  wording in Done reports (§ 6 notes the corrections, which match CR2-01's
  text); S003 CR1-08 was declined at Gate B; S001 CR1-09 / CR2-01 were rejected.
- **Base pattern.** A full-page view in `<router-view>` with the shell intact
  follows § Overall Layout; "don't leave the view blank" (§ View Structure) is
  the point of the step. No departure.
- **Dependency.** "Depends on: S004 committed" is right: S004 is in the working
  tree uncommitted, and S005's code-review diff must not include it.
- **Header block, status `In review`, README index row:** present and correct.
