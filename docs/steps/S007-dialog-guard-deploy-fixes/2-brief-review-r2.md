```
Step: S007 — Dialog close guard; Nginx and deploy fixes
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S007 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** All nine round-1 answers
are in the brief text, not only in the Review log. The new § 5.1 "one gate" on
`hide.bs.modal` is sound: I traced every close path through Bootstrap 5.3.8's
`modal.js`, `util/component-functions.js`, `util/focustrap.js` and
`dom/event-handler.js`, and the brief's claims hold. The four `minor` findings
are details of that gate the coder would otherwise have to settle alone (how
the listener is attached, the form still submitting while the bar shows, ✕
while the bar shows, and the timing of the two focus moves); the two nits are
small.

What I checked against: the working-tree `FormModal.vue`, `useFormModal.js`,
`useMasterForm.js`, `ActiveToggle.vue`, all ten `FormModal` dialogs,
`PhotoViewer.vue`, Bootstrap 5.3.8 in `node_modules` (`js/src/modal.js`,
`util/component-functions.js`, `util/focustrap.js`, `dom/event-handler.js`),
`tooling/build/nginx.conf`, the devops `deploy.yaml`, `compose.yml.j2`,
`docs/lob-apps/Yantra.MD`, the `geo/` and `oneerp/` deploys, `Plan.MD`,
`example_secrets_app.py`, the base § Form / Modal Pattern, and the frontend test
setup. The S007 folder is untracked, so there is no `git diff` of the brief; I
compared the revised text against the round-1 findings directly.

## Round-1 answers verified in the brief text

| Finding | Marked | Where it now stands in the brief | OK |
|---|---|---|---|
| BR1-01 | Accepted, option 1 | § 3: `keyboard` stays `true`, one `hide.bs.modal` gate, `allowHide`, ✕/Cancel keep `data-bs-dismiss`; § 5.1 gate order and corrected Esc bullet; § 7 row rewritten with the rejected `keyboard: false` alternative | yes |
| BR1-02 | Accepted, (a) | § 3 (`UserUnitsPanel` re-takes its snapshot after `save()` re-fills), § 5.2 ("The review found one"), § 8 manual check "Add user with the name of a user who already has access" | yes |
| BR1-03 | Accepted, (a) | § 1 out of scope: Deactivate / Reactivate keeps today's behaviour | yes |
| BR1-04 | Accepted, (a) | § 5.4 "Why" rewritten (mount re-bound only on start; recreate is the proven fix), YAML comment corrected, redundant second recreate stated under "Accepted" | yes |
| BR1-05 | Accepted | § 2: "use error robustness" (2020), "error tolerance" (2006), plain-terms reading | yes |
| BR1-06 | Accepted | § 5.2: `dirty` is `false` while `snapshot` is `null`; `openCreate`/`openEdit` set it to `null` first | yes |
| BR1-07 | Accepted | § 5.2: fixed comparator, `undefined` note, `instanceof` on reactive values; § 8 test case | yes |
| BR1-08 | Accepted | § 3 / § 8: `frontend/tests/formSnapshot.test.js`; `:disabled="saving"` on ✕ and Cancel (§ 3, § 5.1) | yes |
| BR1-09 | Accepted | § 5.1: Keep editing returns focus to the remembered element; § 8: "the cursor is back in the field" | yes |

## The "one gate" against Bootstrap 5.3.8 (`js/src/modal.js`)

What the brief claims, and what the source does:

- **`hide()` fires a cancellable event first and stops when prevented.** Lines
  123–141: `hide()` returns at once if not shown or transitioning; triggers
  `hide.bs.modal` (128); if `defaultPrevented`, returns (130–132) before
  `_isShown = false`, before `_focustrap.deactivate()` (136) and before the
  `show` class is removed. `dom/event-handler.js` 282–289 builds it as a native
  `new Event(name, { bubbles: true, cancelable: true })` and dispatches it on
  the element, so a plain DOM listener's `preventDefault()` is seen. The
  brief's "no shake, no focus change" is right: nothing after the check runs,
  and the focus trap stays active.
- **Esc with `keyboard: true` goes through `hide()`.** Lines 207–218: the
  keydown listener on the modal element calls `this.hide()` when
  `keyboard` is true; `_triggerBackdropTransition()` (the shake) only runs
  when it is false. So Esc passes the same gate, as § 5.1 says. (Esc while
  the dialog is still fading in returns early at 124–126 — today's behaviour,
  fine.)
- **`data-bs-dismiss` goes through `hide()`.** `util/component-functions.js`
  16–30: a document-level click delegate; `isDisabled(this)` returns first
  (21), so `:disabled="saving"` is a true no-op; otherwise
  `this.closest('.modal')` → `getOrCreateInstance(target).hide()` — the same
  instance, the same gate.
- **An outside click with the static backdrop never calls `hide()`.** Lines
  226–242: `backdrop === 'static'` → `_triggerBackdropTransition()` (264–290):
  `hidePrevented.bs.modal`, the `modal-static` shake, and `this._element.focus()`
  at 289. See BR2-06 for that last line.
- **`allowHide` on `close()` and Discard.** Both call `hide()` with the flag
  set, so step 1 of the gate lets the event through and Bootstrap closes
  normally. `useFormModal.finish()` → `modal.close()` is also the path for
  Deactivate / Reactivate (`useMasterForm.changeActive` → `base.send` →
  `finish`) and for `UserUnitsPanel.save()`, so those close without the
  question — consistent with the BR1-03 decision. See BR2-05 for the flag's
  lifetime.
- **Config.** `Modal.getOrCreateInstance(el, { backdrop: "static" })` applies
  the option at creation (the only time it is read); `keyboard` defaults to
  `true` (line 53).

## Findings

### BR2-01 (minor) — Say how the listener is attached: a native `addEventListener`, not a template `@hide.bs.modal`

**Problem.** § 3 and § 5.1 say "a listener on Bootstrap's cancellable
`hide.bs.modal` event" without saying how. The obvious Vue form,
`@hide.bs.modal="onHide"` on the root `<div>`, does not work: Vue reads
`.bs` and `.modal` as event modifiers and listens for an event named `hide`,
which Bootstrap never fires. The gate would then never run, and every close
path would close at once — silently, since the static backdrop still works
on its own.

**Why it matters.** The whole of Part A rests on this one listener; the coder
should not have to find the trap by a failing manual check.

**Options.** (a) In `onMounted`, next to `getOrCreateInstance`:
`el.value.addEventListener("hide.bs.modal", onHide)`, and the matching
`removeEventListener` in `onBeforeUnmount` before `dispose()` (recommended;
the event is a native `Event`, so `event.preventDefault()` is all the handler
needs). (b) Bootstrap's own `EventHandler.on(el, "hide.bs.modal", …)` from
`bootstrap/js/src/dom/event-handler` — works, but reaches into Bootstrap's
internals for no gain.

### BR2-02 (minor) — The form can still be submitted while the confirm bar shows

**Problem.** Two routes past the bar that § 5.1 ("Save can't be clicked past
it") does not close:

1. **Keep editing** and **Discard** sit inside `<form … @submit.prevent="$emit('save')">`.
   A `<button>` without `type` defaults to `submit`, so a click on Discard
   would emit `save` (and save a form the user meant to throw away) before
   its own handler closes the dialog. The existing Cancel and the
   `ActiveToggle` buttons all carry `type="button"` for this reason.
2. **Enter in a text field.** HTML's implicit submission submits a form that
   has no visible submit button when it has at most one text-like field, and
   a `display: none` submit button still acts as the default button. So in
   the one-text-field dialogs (Edit title; Unit access, whose checkboxes
   don't count), the user who presses Esc, gets the bar, clicks back into the
   field and presses Enter saves without answering the question. The body
   fields stay editable while the bar shows (only the footer changes), so
   this is reachable.

**Why it matters.** Both are a single keystroke or click, and both bypass the
question the step exists to ask.

**Options.** (a) `type="button"` on Keep editing and Discard, and make the
submit handler a no-op while the bar shows (e.g. a `submit()` method:
`if (confirming) return; emit("save")`) — recommended, two lines. Add to § 8:
"Edit title: type, Esc, click in the field, Enter → nothing happens". (b)
Disable every field while the bar shows — heavier, and the user may want to
re-read what they typed.

### BR2-03 (minor) — ✕ while the bar shows reaches gate step 3; say what it does

**Problem.** Step 3 of the gate reads "the confirm bar is showing (so this is
Esc) → prevent, hide the bar". But ✕ keeps `data-bs-dismiss` and stays in the
header while the bar replaces only the footer, so a click on ✕ also calls
`hide()` and lands in step 3. The gate cannot tell the two apart (the
`hide.bs.modal` event carries no source). As written, a user who presses ✕
twice sees the question vanish, presses ✕ again and gets it back: a toggle,
not an answer.

**Why it matters.** § 5.1 is the contract the manual checks test against; "✕
→ the bar" is in § 8 but "✕ again" is not defined.

**Options.** (a) `:disabled="confirming || saving"` on ✕, so the bar's two
buttons and Esc are the only answers and step 3 is truly Esc (recommended:
one binding, and `isDisabled` in `component-functions.js` line 21 makes the
click a no-op, so no event reaches the gate). (b) Keep it and state "Esc or
✕ while the bar shows = Keep editing" in the § 5.1 table.

### BR2-04 (minor) — The two focus moves need `nextTick` and a fallback, or Esc goes dead

**Problem.** § 5.1 promises that focus moves to Keep editing when the bar
shows, and back to the remembered element on Keep editing. Two timing facts
the brief should state:

1. The bar is rendered on the tick after the gate flips its flag, so a
   `focus()` on Keep editing inside the `hide.bs.modal` listener finds no
   element yet. It has to run in `nextTick`.
2. When the element that had focus is removed (Cancel is replaced by the
   bar; later the Keep editing button is removed when the bar hides), the
   browser moves `document.activeElement` to `body` **without firing
   `focusin`**. Bootstrap's focus trap (`util/focustrap.js` 88–104) only acts
   on `focusin`, and its Esc listener sits on the modal element (`modal.js`
   207), which a keydown on `body` never reaches. So until the next Tab or
   click, Esc does nothing. The restore therefore has to succeed, and it can
   fail: Cancel exists again only after the bar's tick, and on iOS Safari a
   tap does not focus a button, so the remembered element may be `body`
   itself.

**Why it matters.** "Esc = Keep editing" and "the cursor is back in the
field" (§ 5.1, § 8) depend on it; a coder who writes the natural synchronous
code gets a dead Esc that only shows up on a phone or after a Cancel click.

**Options.** (a) Both moves in `nextTick`; after restoring, if
`!el.value.contains(document.activeElement)` then `el.value.focus()` — the
modal root, which is what Bootstrap itself focuses (`modal.js` 289) and where
its Esc listener is (recommended; three lines). (b) Remember nothing and
always focus the modal root on Keep editing — simpler, but drops BR1-09.

### BR2-05 (nit) — Clear `allowHide` right after `hide()` returns, not only in `open()`

`hide.bs.modal` fires synchronously inside `hide()`, so `close()` and Discard
can do `allowHide = true; try { modal.hide() } finally { allowHide = false }`.
The reason: `hide()` returns without firing the event when the dialog is
still transitioning (`modal.js` 124–126), and then the flag would survive on
a dialog that is still open, so the next Esc would skip the question.
Unlikely (a save within the 300 ms fade-in), but the fix is free and makes
the flag's lifetime obvious. `open()` clearing it too is harmless.

### BR2-06 (nit) — An outside click moves the focus to the modal root

§ 5.1 says the static backdrop "shakes the dialog slightly instead, which is
kept as the feedback". It also moves the focus: `_triggerBackdropTransition`
ends with `this._element.focus()` (`modal.js` 289), so a user who clicks
outside by mistake and comes back has to click into their field again (the
typed text is intact). That is Bootstrap's standard behaviour and acceptable
here; one clause in § 5.1 ("and takes the focus; the text is kept") stops the
coder or the manual tester from reading it as a bug. Suppressing it would
mean handling `hidePrevented.bs.modal`, which is not worth it.

## Standards, in plain terms

The citations are correct and the step touches no maintenance standard
(TPM, ISO 14224, EN 13306, ISO 55000, SMRP) — it is about the tool.

- **ISO 9241-110:2020, use error robustness** (the 2006 edition's "error
  tolerance"): an interactive system should make slips hard to make and, when
  one happens, keep the user's work and offer a cheap way back. The static
  backdrop removes the slip; the in-dialog question is the cheap way back; and
  asking only when there is something to lose keeps the question meaningful.
- **Nielsen's heuristic 5, error prevention**: design the error away rather
  than report it afterwards — the same point.
- **ISO 27001:2022 A.8.9, configuration management**: configurations of
  hardware, software and services are established, documented, implemented,
  monitored and reviewed. A `secrets_app.py` rewritten on disk but not read by
  the running container is undocumented drift between "deployed" and
  "running"; the recreate-on-change task removes it.
- **ISO 27001:2022 A.8.32, change management**: changes to information
  processing facilities follow a defined, repeatable procedure. The two manual
  steps of 15-10-2026 become playbook tasks, so the next deploy repeats them
  the same way without anyone remembering to.

## Checked and found consistent

- **Round-1 answers** — all nine are in the brief text (table above).
- **The gate's five steps** cover every path: Esc (`modal.js` 212–214), ✕ and
  Cancel (`component-functions.js` 29), `close()` and Discard (`allowHide`),
  Save → `finish()` → `close()` after `saving` is already `false` (the
  `finally` in `useFormModal.send` runs before `finish`). An outside click
  and a tap on a phone never reach `hide()` (static backdrop, 233–236).
- **No focus or shake on a prevented hide** — `hide()` returns before
  `_focustrap.deactivate()` and before any class change; the shake lives only
  in `_triggerBackdropTransition`, which `hide()` never calls.
- **The ten dialogs**: Sites, Units, Classes, Types, Unit access, Equipment
  create/edit, Move, Status, Upload, Title — exactly ten `<FormModal>` uses in
  `src/`. Their open paths fill the form synchronously before or within the
  tick of `modal.open()`, so a `nextTick` snapshot is right: the equipment
  dialog's one-unit preselect runs inside `openCreateEquipment`'s synchronous
  `prepare()`; the status dialog's "No" sets `form.status` back to the
  record's value, which the by-value comparison reads as unchanged; the upload
  dialog's `watch(kind)` runs pre-flush and sets `file` from `null` to `null`;
  the move dialog's search and `chosen` live outside `form`. The equipment
  dialog's site `<select>` is also outside `form` (its `@change` clears
  `unit_id`), so changing only the site is "not a change" by the same reasoning
  § 1 gives for the move search box — consistent.
- **`UserUnitsPanel`** does not use `useFormModal`; `username` (string) and
  `selected` (a `Set`) are what its own `dirty` must compare, and the one
  later re-fill is the `load(...)` inside `save()`, as § 3 says.
- **`PhotoViewer.vue`** has its own `Modal` and its own `data-bs-dismiss` ✕;
  unaffected.
- **`formSnapshot` home and tests**: `frontend/src/utils/` holds `datetime.js`,
  `equipmentLabels.js`, `format.js`, so `formSnapshot.js` fits; `vite.config.js`
  sets `environment: "jsdom"` (jsdom 29), so `File` exists in tests; vitest
  4.1 finds `tests/formSnapshot.test.js` by default.
- **Existing tests**: the five frontend tests touch nothing in Part A; no
  backend change. S006's parallel fix round touches `documents.py` and its
  tests, not `FormModal.vue`, so the "S006 committed" dependency is only about
  the `saveLabel` line in `FormModal.vue`.
- **Nginx** (§ 3, § 5.3): `resolver 127.0.0.11 valid=10s ipv6=off;` and `set`
  are valid in a `location`; a variable `proxy_pass` with no URI passes the
  request URI unchanged, matching today's `proxy_pass http://backend:5000;`;
  the resolver is required with a variable `proxy_pass`; `valid=10s` matters
  because Docker's DNS answers carry a long TTL. `nginx -t` does not resolve
  names, so the local check in § 8 works offline.
- **Deploy** (§ 5.4): `register: secrets_file` → `when: secrets_file.changed`
  is standard; `docker_compose_v2` with `project_src`, `files`, `services` and
  `recreate: always` is the form already used in `erp_server/geo/deploy.yaml`
  (line 83) and `erp_server/oneerp/deploy.yaml` (line 85); backend and worker
  have no `depends_on`, so recreating them touches nothing else; the frontend's
  `depends_on: backend` does not recreate it, which is why Part B item 4 is
  needed; the health check (24 × 5 s) outlasts `stop_grace_period: 35s`.
- **`Yantra.MD` step 5**: says `vel-yantra`; `Plan.MD` (login row and the
  12-10-2026 decision) and `example_secrets_app.py` say `vel-yantra-master`.
  The correction is right.
- **Plan.MD**: nothing in its decisions mentions dialogs, Nginx or the deploy
  path; no conflict.
- **Base pattern** (§ Form / Modal Pattern, "Never lose typed input"): static
  backdrop, in-dialog question, snapshot at open, no `confirm()`, implemented
  once in the shared component — the brief follows every clause.
- **Scope and size**: two fixes, no new dependency, the devops-repo question
  left to the user (§ 9.1). Not over-engineered.
