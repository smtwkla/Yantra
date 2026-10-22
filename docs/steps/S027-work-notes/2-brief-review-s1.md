```
Step: S027 — Work notes
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 22-10-2026
```

Reviewed against: 79fc61d + uncommitted S026

# S027 — Staleness review, round s1

**Verdict: no `blocker` or `major` finding. The brief's design holds against the
working tree. One `minor` (the e2e run the brief asks for is now the wrong size)
and three `nit`s (stale wording).**

Scope: the files the orchestrator named, from `bbaed12` to the working tree
(commits `c7e6396`, `79fc61d`, the "doc" commits, and uncommitted S026 at gate B).
Only the one question is answered: does each statement of the brief about that
code still hold? The rest of the brief is not re-reviewed.

## The focus question (§ 1.2, § 3): S027's `autofocus` and S026's `revealError`

**Fact: the two focus calls cannot fight, and the e2e wait still behaves.** The
sequence in the code now:

1. `FormModal.open()` calls `modal.show()`. Bootstrap (`modal.js`
   `_showElement`) resets `modal-body.scrollTop`, adds `show`, and at the end of
   the fade runs `transitionComplete`: `_focustrap.activate()` first, which
   focuses the **modal element** (`focustrap.js:68`, `trapElement.focus()`),
   then it fires `shown.bs.modal`.
2. S027's `shown.bs.modal` handler then focuses the first `[autofocus]` element
   in the body. That element is inside the modal, so the trap's `_handleFocusin`
   returns at once (`trapElement.contains(event.target)`). Both focus moves run
   in one JavaScript task.
3. S026's `revealError` runs only on a refusal: `useFormModal`'s `watch(error)`
   and `FormModal`'s `watch(() => props.error)`, both `flush: "post"`, both
   skipping a falsy value. `openCreate`/`openEdit` set `error` to `null` before
   `open()`, so nothing reveals at open. The two calls never run at the same
   moment: one at open, one after Save.
4. The e2e `openDialog()` (S026 A1) waits until `.modal.show` contains
   `document.activeElement`. After step 1 that is the modal element; after step
   2 the textarea. Both are inside `.modal.show`, and a `waitForFunction` poll
   cannot land between the two (one task). So `openAction()` returns with the
   cursor already in the *Note* field, and `expect(field).toBeFocused()` right
   after it is not a race.

**Fact: no existing dialog carries `autofocus`** (`grep autofocus frontend/src`
finds nothing), so the new listener changes nothing for the other 20 dialogs.
The brief's "Any later dialog can use it" holds.

## Findings

### BS1-01 — `minor` — The brief asks for the targeted e2e run; the rule now needs the full suite

**Problem.** Since the baseline, `docs/steps/README.md` § Manual checks,
`.claude/CLAUDE.md` (Browser tests) and the coder and code-reviewer prompts say:
the **targeted** specs plus `screens.spec.js` by default; the **full** suite
only when the step changes shared frontend code, and `FormModal.vue` is the first
file on that list (decided 22-10-2026). S027 changes `FormModal.vue` (§ 3, the
`shown.bs.modal` focus). The brief says only "the e2e spec passes on the three
projects" (§ 8 Acceptance) and names `tickets-notes.spec.js` and
`tickets-work.spec.js` (§ 3 Tests). A coder who follows the brief runs two spec
files and `screens.spec.js`.

**Why it matters.** The new listener runs on every dialog open in the app. The
full run is what proves the other 20 dialogs did not change (S026 saw WebKit
lose typed text around exactly this moment, `shown.bs.modal`).

**Options.**
- **(a) Recommended:** § 8 Acceptance: "The **full** e2e suite
  (`tooling/run-e2e-tests.bat`, in lanes) passes, because `FormModal.vue`
  changes (README § Manual checks); the new spec and `tickets-work.spec.js`
  on the three projects." One line in § 3 under `FormModal.vue`: "shared code,
  so the coder and the code reviewer run the full suite".
- (b) Leave it to the coder's prompt, which carries the rule. The brief then
  contradicts the prompt, and the next reader of the brief sees the wrong size.

### BS1-02 — `nit` — The `tickets-work.spec.js` line number is stale

**Problem.** § 3 Tests names the engineer test as "line 217". S026 added a test
above it; the test now starts at line 237 and `card(page, "Description")` is at
line 248. The test's title is unchanged: "engineer: assign, edit and change
severity; IT admin with no Team record acknowledges as nobody". The assertion
still exists, so the statement is right in substance.

**Fix.** Name the test by its title and drop the line number; the title is
what the impl report's `[auto]` lines use anyway.

### BS1-03 — `nit` — The "either order" hedge and the Baseline are out of date

**Problem.** The introduction says "If S026 is not done first, the coder uses
the dialog pattern as it is … in either order (BR1-06)". S026 is now in the
working tree (gate B, uncommitted), so the coder works on top of it. The hedge
is harmless but no longer describes the situation, and the `Baseline:` line
still says `bbaed12`.

**Fix.** Replace the hedge with the facts the coder relies on: S026's
`revealError.js` searches `.is-invalid, .invalid-feedback.d-block,
.alert-danger` inside `.modal-body`, which the note field's markup matches
(§ 3), and the 409 "This ticket is closed" reaches the top bar through
`modalError` → the `error` prop, which `FormModal`'s prop watch scrolls into
view (§ 5.3). Set `Baseline:` to `79fc61d + uncommitted S026` after this
review, as README § Stale brief check step 2 says.

### BS1-04 — `nit` — § 1.2 and § 8 can state the focus sequence and the e2e helper in one line each

**Problem.** § 1.2 says Bootstrap "focuses the modal itself when it opens",
which is right, but it does not say that the `shown.bs.modal` handler runs
after that focus and so wins. § 8's "the cursor is in the field" does not say
how the test checks it. Both are now settled by code that did not exist at the
baseline (`openDialog`'s focus wait, S026 A1), and the coder would otherwise
re-derive the sequence above.

**Fix.**
- § 1.2 or § 3 `FormModal.vue`: "Bootstrap's focus trap focuses the modal
  element, then fires `shown.bs.modal`; the handler moves the focus on to the
  `[autofocus]` element, inside the trap, so the trap leaves it there.
  Register it with `addEventListener` in `onMounted`, as `hide.bs.modal` is
  (a template `@shown.bs.modal` would be read by Vue as the event `shown` with
  modifiers; the file's comment says so)."
- § 8 Automated, first check: "open the dialog with `openAction()` (it waits
  for the focus to be inside the modal, S026 A1), then
  `expect(dialog.getByLabel("Note")).toBeFocused()`, as
  `tickets-work.spec.js`'s S026 test does for the hours field. Type into a
  dialog only after `openDialog()`/`openAction()` returns."

## Checked and found consistent

- **`FormModal.vue` and `useFormModal.js`**: the brief's claims about them hold.
  `revealError` is exposed and called from both watches; `open()` still goes
  through `modal.show()`; no `shown.bs.modal` listener exists yet, so S027 adds
  the first one. The `hide.bs.modal` and `hidden.bs.modal` listeners are added
  in `onMounted` by `addEventListener`, the pattern S027's listener follows.
- **`revealError.js`** (new in S026): its selector finds the note field's
  `is-invalid` and the message's `invalid-feedback d-block` (§ 1, § 3), and for
  an `.is-invalid` textarea it focuses the textarea itself. Nothing in it runs
  at open.
- **`e2e/support/dialogs.js`**: `openDialog` is now `async` and waits for the
  focus; `expectDialogFits` and `openAction` (`tickets.js`) call it, so the new
  spec needs no helper change. `expectFieldMessage` uses `toBeInViewport()`,
  which is what § 8's "'Enter a note' under the field, in view" needs.
  `saveDialog` deliberately does not wait for focus (the comment says why);
  the brief does not depend on that.
- **`tickets-work.spec.js`**: the engineer test still reads
  `card(page, "Description")` after the *Edit* dialog, and
  `TicketDetailView.vue` still has the *Description* card (line 411), so § 1.4
  and § 3's change to that test still apply.
- **Lanes (`run_lanes.py`, `stack.js`, `playwright.config.js`)**: three
  projects, unchanged; a lane runs several spec files on one database, so the
  50-ticket cap of the open-tickets list still applies within a lane and the
  spec's `afterEach` close (§ 3 Tests) is still needed. S026's own labour test
  adds "not on the extruder" for the same reason; the coder may do the same.
- **Docs the planner owed at approval (§ 3 Docs)**: done in the working tree.
  `docs/Plan.MD` § 3 has the `ticket:edit_notes` row and the site-scoped
  sentence; § 4.2 has the work-notes text; `.claude/CLAUDE.md` SMTW-Review
  maps `tickets-notes` to S027.
- **`device-checks.md`**: S026 added row 12; the brief refers to its row by
  section, not by number, so § 8 *On a real device* still holds (it becomes
  row 13).
- **S026's open findings** (CR1-03 to CR1-06, test and report wording) touch
  no file S027 relies on.
- **Backend files** (`tickets.py`, `tickets_core.py`, `config_rbac.py`,
  `local_db.py`, the test files): not in the diff since the baseline; the
  brief's statements about them were verified in round 1 and are unchanged.
