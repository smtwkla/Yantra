```
Step: S103 — Help: a link in the app to the user guide in the gallery
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 02-11-2026
```

# S103 — Code review, round 3

**Verdict: no `blocker` or `major` finding is open.** Fix round 2 fixes CR1-01 (by KLA's option a),
CR2-01 and CR2-02. It brings in no new fault, and this round has no new finding.

## Tests run

- All suites, `YANTRA_TEST_RUN=s103cr3 tooling/run-tests.bat`: **PASSED**. Backend 5310 passed
  (276 s), frontend 458 passed, tooling 258 passed (`scratch/s103cr3-all.out`). The round changed
  code in `frontend/` and `tooling/`, so I ran all suites.
- Build check, `npx vite build` in `frontend/`: passed (exit 0; only the usual chunk-size warning,
  `scratch/s103cr3-build.out`).
- Browser tests: I ran none, because no finding of mine needs one. The coder's targeted run is
  right for the round: `floor`, `notifications` and `screens` gave 39 passed and 5 skipped
  (`scratch/s103f2-e2e.out`, 16:21). The round changed a `@device` test, so the coder also ran the
  S103 tests on `phone-webkit`: 2 passed (`scratch/s103f2-webkit.out`, 16:22). Both runs come after
  the last change to `AppTopbar.vue` (16:17) and `floor.spec.js` (16:17).

## Status of the earlier findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Fixed (KLA 02-11-2026, option a) |
| CR1-02 … CR1-10 | minor / nit | Fixed in fix round 1 (verified in round 2) |
| CR2-01 | nit | Fixed |
| CR2-02 | nit | Fixed |

How I verified each fix:

- **CR1-01, the phone top bar.** Below 576 px, `.topbar-left` (the word "Yantra") now has
  `display: none` (`AppTopbar.vue:129-131`). Round 1's phone rules are gone: Help and the bell
  keep the 44 × 44 px of `:100-109`, and Sign out keeps its icon and its word (`:51-53`, S064
  UX-02). Against the state before the step, the phone block differs only in two ways: the brand
  word is hidden instead of set to 0.8 rem, and the name cap (4.5 rem, margin 0.25 rem) is kept.
  The cap is still needed. My estimate at 360 px: the bar has 336 px inside its padding. Help (44)
  plus the bell (44) plus the capped name (76) plus Sign out with icon (about 106) leave about
  66 px for the title. The seeded operator's name, "Muthu (operator)", is wider than the cap, so
  the test runs the worst case. On desktop nothing changed in this round: the brand word shows,
  and `.topbar-center` keeps `flex: 1 1 auto` with centred text, as reviewed in round 1.
- **The strengthened `@device` test** (`floor.spec.js:98-118`). It now asserts, for Help, the bell
  and Sign out, a width of at least 44 px beside the height. It also asserts that Sign out's icon
  is visible. Each of the three round 1 rules (36 px icons, the hidden icon) would fail one of
  these asserts. The test keeps the title checks (in view, at least 60 px) and no sideways scroll.
  The tag `@device` still fits the rule: the test's main assertions are geometry. The missing red
  run has a reason (it needs round 1's CSS put back), so it is not a finding.
- **CR2-01.** The cover line names the date once (`help/guide/index.html:184`). `help/README.md`
  step 3 now names the Help home, the cover and the last slide (`:1199`, which holds the version).
- **CR2-02.** `test_help_pages.py:80-88` collects the spellings of every folder prefix of each
  path, the whole path included (`end` runs to `len(parts)`). So `Shots/a.webp` beside
  `shots/b.webp` now fails, as in the collector's `_case_clashes`. The message lists the clashing
  spellings. The missing red run has a reason (the pages are valid), so it is not a finding.

## Findings

No `blocker`, `major`, `minor` or nit finding is new in this round.

## Manual checks

The impl report's `## Manual checks` still carries every important check of the brief. Still for
the user:

- [ ] **Important.** Open `help/guide/index.html` from disk at about 1366 × 768 and at 360 px, and
  `help/documents/index.html` at 360 px and at 1366 px.
- [ ] **Important.** On a phone at 360 px, the top bar: Help, the bell and Sign out with its icon.
  The title has about 66 px, so a long title such as "My notifications" ends in "…". Judge whether
  that is enough on the floor; the hamburger menu queued for later is the way to more room.
- [ ] **Important.** Device-checks row 69, after the release and the first publish.
- Device-checks row 70.

## Checked and found consistent

- Files re-read: the fix round's diff of `AppTopbar.vue`, `floor.spec.js`,
  `test_help_pages.py`, `help/README.md` and `help/guide/index.html`; `AppTopbar.vue` in full;
  `floor.spec.js:85-118`; the whole step's diff of `AppTopbar.vue`; `help/guide/index.html:1195-1200`.
- Facts checked against their source: `.tap-target` is only `min-height: 44px`
  (`frontend/src/assets/main.css:142`); the operator's seeded name (`tooling/e2e/seed_e2e.py:38`).
- No spec, unit test or help-tour file reads `.topbar-left` or the brand word, so hiding it on
  phones breaks no test.
- The guide's phone shots still show the brand word and no Help link. The impl report states this,
  and the guide says its screens show v0.1.15, so the shots are not wrong.
- The round's `## Docs updated` names `help/README.md`. No other doc in *Docs to keep current* is
  due: no migration, secret, role or maintenance rule changed.
- The round stays inside the three findings. It touches no shared frontend file of the settings
  (*Shared code*).

## Feedback

- none
