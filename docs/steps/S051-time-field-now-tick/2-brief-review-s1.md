```
Step: S051 — The time field shows the time, with a Now tick
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 + uncommitted S047 (snapshot `refs/steps/S047` = 39d9477; the other uncommitted changes are step documents of S050–S052 only)

# S051 — staleness review, round s1

**Verdict: no blocker or major finding. The design and every approved decision still hold.** Two
`minor` findings on the brief's test section: the run instruction now reads as the Full level,
and S047's tag rule needs a word on the layout test. Two nits.

**What changed since the baseline that S051 relies on** (S047, gate B, not committed):
- `frontend/e2e/readings.spec.js`, `tickets-raise.spec.js`, `tickets-work.spec.js`,
  `screens.spec.js`: Playwright tags only (`@device`, and `@smoke` in `screens.spec.js`). No
  assertion, helper or line the brief cites moved.
- The run rules: `tooling/run-e2e-tests.bat --level=basic|normal|full` (no flag is Normal). The
  coder makes targeted Normal runs, runs the whole suite at Normal once when the coding is done,
  and never runs Full (release only). `docs/steps/README.md` § Manual checks, `.claude/CLAUDE.md`
  § Browser tests, `.claude/agents/coder.md`.
- The tag rule (S047 brief § 1.3): a test whose purpose is a layout check gets `@device`; a logic
  test stays untagged, also when it calls `expectDialogFits` or asserts one geometry inside a
  flow.
- `docs/Plan.MD`: two lines inserted after line 725 (S050, S052). Lines 723 and 725 are where the
  brief says.

Nothing in `frontend/src/` changed since the baseline: `EventFields.vue` and the five screens are
as the brief describes them.

## Findings

### BS1-01 — minor — § 5: "the full suite once at the end" now names the wrong level

**Problem.** § 5 opens: "Automated (e2e, targeted: `readings.spec.js`, `tickets-raise.spec.js`,
`tickets-work.spec.js`, plus `screens.spec.js`; the full suite once at the end)". Since S047,
"Full" is a level: every test on three devices, the iPhone in Docker, release only. The coder's
rule is now: targeted runs at Normal, then **the whole suite at Normal once** when the coding is
done; Full never (`.claude/agents/coder.md`, README § Manual checks).

**Why it matters.** A coder who reads "the full suite" as `--level=full` breaks the S047 rule,
needs Docker Desktop, and spends about three times the run. The wording was right at the
baseline; the vocabulary changed under it.

**Options.**
- (a) **Recommended.** Reword: "Automated (e2e). Targeted Normal runs with `readings.spec.js`,
  `tickets-raise.spec.js`, `tickets-work.spec.js` and `screens.spec.js`; the whole suite at Normal
  once when the coding is done (S047). Never the Full level."
- (b) Delete the run instruction and leave it to `coder.md`. Loses the list of targeted specs,
  which the coder needs.

### BS1-02 — minor — § 5: the layout test needs its tag, and its device, stated

**Problem.** The fifth S051 test reads: "on a phone (Pixel 7) the input and the *Now* box fit on
one line inside the dialog (`expectDialogFits`), and the *Now* box's tap area is at least 44 px
high (bounding box …)". By S047 § 1.3 rule 1, a test whose title names a fit and whose main
assertion is a geometry gets `@device`. The brief, written before the rule, says nothing about
tags. Two readings are possible:
- tagged `@device`: at Normal it runs on `phone-chromium` **and** `desktop-chromium`, so "on a
  phone (Pixel 7)" no longer describes where it runs;
- untagged: the code reviewer, now told to raise a wrong or missing tag (S047, `code-reviewer.md`),
  will ask.

The other four S051 tests are logic tests and stay untagged under the rule; the brief need only
say so in one line.

**Why it matters.** The coder would decide the tag alone, and the title and the device framing
must agree with it. The 44 px rule is plain CSS (`min-height: 44px`, no media query in the S040
pattern, `ReadingsView.vue:425`), so the assertion holds on desktop too.

**Options.**
- (a) **Recommended.** Tag it `@device`. Title it as a layout check ("S051: the time input and
  the Now box fit on one line, and the box is 44 px high"). Drop "on a phone (Pixel 7)": the
  assertions hold on every device, and Normal runs it on both Chromium projects. Add: "the other
  S051 tests are logic tests, untagged (S047 § 1.3)."
- (b) Fold the two geometry assertions into the first S051 test (*Log reading* opens ticked …),
  untagged, as the S040 A1 test does with *Enter more readings* (`readings.spec.js:673`). Cheaper
  at Normal; the layout then gets checked on the iPhone and desktop only at Full, in the release.

## Nits

- **BS1-03** (nit) § 3, `readings.spec.js`: "three S040 A1 tests assert the *Change* button" — it
  is two tests with three assertions (`:669` and `:683` in the full-save test, `:756` in the
  CR4-01 test). Write "two S040 A1 tests (three assertions)". Pre-existing, not from S047.
- **BS1-04** (nit) § 5, the real-device line "Before a release, with the rest of phone-webkit":
  since S047 that is "in the release's Full run (`tooling/release-tests.bat`)". Say so, so nobody
  looks for a separate phone-webkit run.

## Checked and found consistent

- `frontend/e2e/tickets-raise.spec.js:155` is still the *Change* click (inside the S018 A1 test at
  `:141`, now `@device`: the brief's change there runs on both Chromium projects at Normal, which
  changes nothing it asserts).
- `frontend/e2e/support/tickets.js`: the doc comment at `:92` and the *Change* click at `:94`, as
  cited.
- The S040 A1 tests the brief names exist (`readings.spec.js:654`, `:740`) and are untagged;
  S047 tagged only the S040 bottom-bar test at `:395`, which S051 does not touch.
- Comment headers: `ReadingFormModal.vue:9` (`frontend/src/views/equipment/`),
  `RaiseTicketView.vue:21`, `MoveDialog.vue:7`, `RegradeDialog.vue:5`, `EventFields.vue:5`, all
  still "Now · Change".
- `docs/Plan.MD` lines 723 (S039, "Now" is the server's clock) and 725 (S040, "Now" sends no
  time) are unchanged; S047's two new lines sit after them.
- `EventFields.vue`, the five screens, the props and the `:key="opens"` remount: no change since
  the baseline, so § 1, § 3 and § 4 hold as approved.
- The brief's change to `e2e/support/tickets.js` no longer triggers a "full suite" rule of its
  own: the whole suite at Normal once (S047) covers it.
- `screens.spec.js` keeps its purpose (every route opens) under its new `@smoke` / `@device`
  tags; the brief lists it as a targeted spec, which still fits.
