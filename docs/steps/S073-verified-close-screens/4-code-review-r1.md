```
Step: S073 — Verified close: screens
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S073 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The screens follow the brief and S072 § 6. The
departures are listed and sound. Four nits remain.

## Test results (my runs)

- All unit suites, `YANTRA_TEST_RUN=s073cr1 tooling/run-tests.bat`: backend 3775 passed (139 s),
  frontend 344 passed, tooling 185 passed. ALL SUITES: PASSED.
- `npx vite build` in `frontend/`: built in 4 s, only the known chunk-size warning.
- Browser tests: none re-run. No finding of mine needs a run. The coder's runs are the right ones:
  - the new tests alone (6 passed);
  - the targeted `improvements.spec.js` + `screens.spec.js` run (41 passed, 1 skipped);
  - the whole suite at Normal once (289 passed, 13 skipped).
  
  The brief asks for the whole-suite run (§ 8.4). No shared file changed (`FormModal.vue`,
  `useFormModal.js`, `api.js`, the router and `e2e/support/` are untouched), so no WebKit run is due.

## Nits

- **CR1-01** (nit) `frontend/src/views/ImprovementDetailView.vue:474`: `.remark-text` repeats the
  `.problem-text, .analysis-text` rule above it. Add it to that selector list instead.
- **CR1-02** (nit) `frontend/src/views/improvements/WatchCard.vue:18`,
  `frontend/src/views/improvements/WatchSummary.vue:17-18`: the machines' codes are joined in both
  components, and the symptoms' labels are joined in `WatchSummary` and `figureRows`
  (`improvementLabels.js:218`). Put one `machinesText(figures)` and one `symptomsText(figures)` in
  `improvementLabels.js` and use them in all three places.
- **CR1-03** (nit) `3-impl-report.md` § 4 D-4: the case it describes does not happen. `_settle_state`
  (`backend/improvements.py:280`) sets `watch_from` to NULL when the state is not *Watching*. On an
  *Actions open* page, `watch.from` is therefore null: the card is hidden and the header carries
  `Change watch`. The code handles both cases, so no code change is needed. Correct the report's
  text.
- **CR1-04** (nit) `VerifyDialog.vue:28`, `DropDialog.vue:20`, `ImprovementNoteDialog.vue:20`:
  `blank` spreads the seed into the form. The brief's call contract (§ 5.3, § 5.5, § 5.6) gives
  `{remark: ""}` / `{reason: ""}` with or without a seed. Drop the `...seed`. Today `open()` passes
  no seed, so nothing breaks.

## Checked and found consistent

- **KLA's plain words.** The badges read *Closed: it worked*, *Closed: did not work* and *Dropped*,
  through S072's `improvementStateLabel`. The buttons read `Close: it worked` and `Did not work —
  analyse again`, and the submit reads `Close and analyse again`. "Effective" appears only in the
  Verify help text ("… records the fix as effective (ISO 9001 § 10.2).") and in the API codes.
  Neither "nonconformity" nor "MTBF" appears. The table says "severity", not "intensity".
- **Writing style B** on every new line:
  - the summary lines, the consequence lines and the help texts;
  - "Ready to verify. An engineer or manager of the site decides.";
  - "Ends on …", "Why drop it?", "Watch for (days)";
  - every button starts with a verb, apart from KLA's chosen "Did not work — analyse again".
  
  The field messages are the server's ("Say why it did not work", "Choose a watch of 30 to 365
  days").
- **The watch card on a phone.** The table is `table table-sm` in `.table-responsive`, with three
  columns. Its labels wrap, so it fits a 412 px Pixel 7. The coder's
  `expectNoSidewaysScroll` passed on the ready page and on the repeat page. The two decision
  buttons are `d-grid gap-2 d-sm-flex`: they stack full width on a phone, `btn-lg`, the danger one
  in outline. No `btn-sm` on the page.
- **The column header.** It is built from `after.days` in every case. It reads "… days after" when
  the record is closed or `watch.ended`, else "… days so far" (D-2's third argument). The e2e test
  asserts "30 days after" on a ready page, and the unit tests cover the running, ended, closed and
  dropped cases.
- **Controls follow S072's flags.** These are shown only by their flag:
  - `Change watch` by `can_edit_watch`: in the header only before the watch, else in the card,
    so one button shows at a time;
  - the decision buttons by `can_verify` (`improvements.py:645`: ready to verify and the key);
  - `Drop improvement` by `can_drop`;
  - `Add note` by `can_add_note`.
  
  All four flags are false on a closed record (`open_now`). The e2e test asserts that none of the
  nine write buttons shows after the close.
- **The Verify dialog.** One dialog with a `mode` ref set by `open(mode)`. The route is picked in
  `send`, and the body is `{remark}` only. The title, the label, the help and the consequence follow
  the mode. The summary line is `WatchSummary` (D-1), so the card and the dialog show the same
  words. On a 409 with no field, the dialog emits `reload`. `load()` keeps the record in place, so
  the dialog stays open with the message.
- **The follow-up navigation.** After a *did not work* save, `afterSave` calls `router.push` to
  the follow-up. `useFormModal.finish` closes the modal first. `FormModal`'s `onBeforeUnmount`
  disposes it once Bootstrap reports it hidden, so no backdrop is left behind. The test lands on
  the new page (badge *Analysing*, *Follow-up of*, *Tickets (1)*), goes back, and reads ", the lead:
  did not work" and *Analysed again in*.
- **The timeline lines.** No line repeats its text:
  - the serial shows, linked, only on `ticket_linked` and `ticket_removed`;
  - the countermeasure's kind and text show only on `action_done` and `action_cancelled`, whose
    remark is the done text or the reason (`improvements.py:1168`, `:1197`);
  - `state_changed` adds "· Now <state>";
  - "Was: …" shows only when both `remark` and `earlier` are set, and a removed why shows its text
    as the row's content;
  - the computed `watch_ended` row shows its time with no person;
  - rows are keyed by index, with `useShowMore` (10, then *Show all n*).
- **`expectDialogFits`** is called on every dialog the six new tests open: Verify in both modes,
  Watch, Drop and Add note.
- **The departures.** Each one is listed in the report, with a reason:
  - D-1, `WatchSummary`: two uses, not over-engineering;
  - D-2, the third argument of `figureRows`;
  - D-3, `repeatText` without the serial, because the serial is a link;
  - D-4, the header line (but see CR1-03);
  - D-5, the MCC1 mill for the set-up, and the gearbox for the repeat test: the repeat test
    asserts its own serial, not a count;
  - D-6, two locator fixes;
  - D-7, the optional symptom argument of `closeByApi`, still in the spec.
- **The header lines.** `watchLine` and `closedLine` match the brief's examples. The close remark
  shows below, `text-secondary`, pre-wrapped. The follow-up links show in both directions. Dates
  go through `formatDate`. `watchEndDate` works on the date part in UTC, so the browser's zone does
  not move it.
- **Tests.** They cover the brief's § 8.1 list and the § 8.2 unit list, with the empty-remark
  refusal on *did not work*. The `S068` serial-link locator is scoped to `ticketRow` (BR1-01). No
  test carries `@device`, which is right: none is a layout test.
- **Docs pass.** `docs/Plan.MD` § 6 is updated, and "Close comes in R05.4" was replaced. The § S072
  paragraph says the screens are built. No migration, secret, role or device check is added. As
  instructed, `.claude/CLAUDE.md` was not edited: the proposed spec-map entry is in the report.
- **Manual checks.** Both important checks of the brief are `[auto]` with their passing tests. The
  brief has no real-device check, and none is needed.
- **Scope.** No backend file, route, key or shared frontend file changed.

## Manual browser check for the user

- None required. If you want to see it once, open a *Ready to verify* improvement on a phone and
  look at the card *Did it come back?*: the table and the two stacked buttons.

## Feedback

- waste: the snapshot diff's `--stat` lists S072's own step files (its brief status and
  `4-code-review-r2.md`), which are outside this step's review
  (`step_snapshot.py diff S073 --stat`, 2 of 17 rows).
