```
Step: S005 — Tidy-up: page not found, leftover review nits
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 15-10-2026
```

# S005 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Three `nit`s, all
wording in the brief; none changes the design. Every round-1 `Accepted` finding
is reflected in the brief text (one of them in § 3 but not quite in § 4.1 and
§ 7: BR2-01). The revised brief was re-checked against the working tree with
S004 in it.

Reviewed against: `1-brief.md` as revised; `2-brief-review-r1.md`;
`backend/equipment.py` (`_read_node`, `_reread`, `_detail`,
`_load_node_for_user`, `_lock_type`, `_check_type_on_update`, `_written_state`,
`create_equipment`, `update_equipment`),
`backend/tests/test_equipment_api.py` (`stale_reread`, `TestRereadAfterWrite`);
`frontend/src/stores/navigation.js`, `tests/navigation.test.js`,
`router/index.js`, `App.vue`, `components/layout/AppTopbar.vue`,
`composables/useDebounced.js`, `views/EquipmentView.vue`,
`views/equipment/EquipmentMoveModal.vue`; `SMTW-WebApp-Base.md` § Frontend
Design and § API conventions; `Plan.MD` (nothing on routing or a not-found
page); `CLAUDE.md`, `CLAUDE-COMMON.md`.

## Earlier rounds — are the accepted findings in the brief text?

| Finding | In the text? | Where |
|---|---|---|
| BR1-01 prefix highlight accepted | Yes | § 4.1 "The sidebar highlights by path prefix … accepted"; the old "highlights nothing" sentence is gone |
| BR1-02 decidable backend test | Yes, and the design is sound (see below) | § 3 Backend; § 5 "Backend: § 3" |
| BR1-03 `landingNavItem` | § 3 yes; § 4.1 and § 7 still say `landingPath` | BR2-01 |
| BR1-04 foreign type last; unknown id left blank | Yes | § 4.5 |
| BR1-05 ISO 9241-110:2020 wording; A.8.28, text not `v-html` | Yes | § 2 |
| BR1-06 the "300 ms" comment | Yes | § 3 EquipmentView bullet |
| BR1-07 `route.fullPath`, wrapping | Yes | § 4.1 |
| BR1-08 Amendments as § 10 | Yes | § 9 "(not used)", § 10 Amendments |

**BR1-02, verified in the code.** The `stale_reread` fixture
(`test_equipment_api.py:476-494`) wraps `insert_row` / `update_row` to set a
flag, and wraps `_read_node` to return `change(row)` once the flag is set. On
create (`equipment.py:463-482`, level `equipment`) the reads after `insert_row`
(`:478`) are exactly two `_read_node` calls: `_written_state` → `_reread`
(`:349`, inside the transaction) and the post-commit `_reread` (`:482`).
Nothing else between them reads a node: `_write_events` only inserts, and
`_detail` (`:182-194`) runs its own SELECTs, never `_read_node` (the only call
sites are `:118` and `:225`, and `:225` is `_load_node_for_user`, which runs
before any write). So a `change` that returns `row` on its first call and
`None` on its second raises the 409 at `:482`, after the commit, with the
fixture unchanged — exactly as § 3 says. `monkeypatch.undo()` before the
assertions, as the existing tests do, means the follow-up list read sees the
real row.

## Findings

### BR2-01 — nit — § 4.1 and § 7 still name `landingPath` where the view needs `landingNavItem`

§ 3 (BR1-03) adds `landingNavItem(permissions)` and derives `landingPath` from
it, and says the view uses the item's label and path. But § 4.1 still reads
"a button to the user's landing page (`landingPath(userPermissions)`), labelled
'Go to <nav label>'", and § 7 says "One rule (`landingPath`) for 'home'". A
coder following § 4.1 literally cannot get the label from `landingPath`.
Also § 5 "Frontend (vitest)" lists only the `canOpenRoute("not-found")` cases,
while § 3 also names the `landingNavItem` tests.

**Fix.** In § 4.1 write `landingNavItem(userPermissions)` ("hidden when it is
`null`"); in § 7 "One rule (`landingNavItem`)"; in § 5 say "Frontend: § 3"
as the Backend line already does, or list both tests.

### BR2-02 — nit — § 4.5: say how the label rule changes, so the coder does not special-case

`typeLabel` (`EquipmentView.vue:84`) switches on *whether a class is chosen*:
`query.class_id ? t.name : "CLS · Name"`. With a class chosen, the foreign
type the brief adds would be labelled by name alone, not `CLS · Name` as
§ 4.5 requires. The one-line rule that gives § 4.5 in both cases is: label
`CLS · Name` whenever the type's class is not the chosen class
(`String(t.class_id) !== query.value.class_id`); with no class chosen that is
every type, as today. Worth a half-sentence in § 4.5 so the coder changes the
rule rather than adding a flag for the appended option. The "(inactive)"
suffix needs nothing: the template (`:194`) appends it for every option.

### BR2-03 — nit — § 3: spell out "the equipment was saved" for the new test

The brief says the test asserts "that the equipment was saved: the mirror of
S002's rollback test". The mirror of `_ids(…) == []` and "next code is `+1`"
(`:511-512`) is: the node **is** in the unit's list, and the next code is
`+2` (the counter was consumed by the committed create). Naming both keeps
the coder from asserting only "a row exists", which would also pass if the
test accidentally hit the in-transaction read on a later refactor. A second
message constant beside `RETRY` (e.g. `RELOAD`) follows from § 4.2.

## Standards, in brief

The brief cites the right ones, and correctly. **ISO 9241-110:2020**
(interaction principles) is the usability standard behind "tell the user where
they are and give an easy way back": *self-descriptiveness* (the screen explains
itself) and *use error robustness* (a user's slip — here a mistyped address — is
recoverable with little effort). **ISO 27001:2022 A.8.28** (secure coding) is
the control that asks for safe output handling; rendering the echoed path with
`{{ }}` and never `v-html` is how a Vue page meets it. **DRY** is the
CLAUDE-COMMON rule behind the single `SEARCH_DELAY_MS`. No maintenance
standard (ISO 14224, EN 13306, ISO 55000, SMRP, TPM) applies: none of the
four changes touches equipment data, maintenance terms or KPIs. Correct to say
so rather than cite one for form.

## Checked and found consistent

- **Catch-all route and guard.** `/:pathMatch(.*)*` placed last in
  `router/index.js` cannot shadow `/equipment/:id(\d+)` or the `/` redirect.
  `canOpenRoute("not-found", …)` is `true` because it is not a nav item
  (`navigation.js:25-28`), so neither the `beforeEach` guard (`:45-49`) nor the
  `App.vue` re-check (`:21-25`) redirects it. The topbar shows
  `route.meta?.title` (`AppTopbar.vue:17`), so "Page not found" is the page
  title. Nothing sets `document.title`, so there is no second place to update.
- **`landingPath` keeps its contract** (`"/equipment"` or `null`), so
  `router/index.js:10,47`, `App.vue:23` and the two `landingPath` tests
  (`navigation.test.js:27-31, 44-46`) are untouched.
- **§ 4.2.** `_reread` takes `message` and `field` (`equipment.py:112`); the
  post-commit calls at `:482` and `:517` pass neither today. The
  `TestRereadAfterWrite.RETRY` constant stays correct for its four tests, which
  all hit the in-transaction read.
- **§ 4.4** matches `_check_type_on_update` (`:309-316`): no lock when the
  type is kept and the class is unchanged (`:313`); `newly_chosen` is
  `"type_id" in clean` (`:316`); the class check always runs (`:283`). The
  first sentence of the docstring, with lock number (5), is kept.
- **§ 4.3.** `EquipmentView.vue:25` and `EquipmentMoveModal.vue:18` each define
  `SEARCH_DELAY_MS = 300`; `useDebounced(callback, delayMs)` has no default
  (`useDebounced.js:7`). The move modal has no other copy of the number; the
  list view's comment at `:120` is the one § 3 renames.
- **§ 4.5 edge cases.** `equipmentTypes` is `null` until loaded: `typeChoices`
  is `[]` and the `v-model` re-syncs when options arrive (`:96-98`), so a late
  load does not blank the applied filter. An unknown `type_id` finds no row
  and appends nothing, which is the "left as is" of § 4.5.
- **Base pattern.** `SMTW-WebApp-Base.md` has no SPA not-found pattern; its
  only 404 rule is for API JSON (`:483`), which the brief keeps out of scope.
  A full view inside `<router-view>` with the shell intact follows § Overall
  Layout.
- **Out of scope, § 6 notes, design table, assumptions:** unchanged from r1
  and still correct. "Depends on: S004 committed" still holds — S004 is in the
  working tree uncommitted; the brief can be approved now, but the coder must
  not start before that commit, or the S005 diff would carry S004's changes.
- **Header block** (status `In review`, revised date) and the README index row
  ("In review — r2") are present and correct.
