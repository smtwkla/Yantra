```
Step: S007 — Dialog close guard; Nginx and deploy fixes
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S007 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01); no `blocker`.** The brief is
accurate about the code it touches and the deploy; the one real gap is that
Bootstrap keeps its own Esc handling even with `keyboard: false`, which
contradicts the focus and Esc behaviour § 5.1 promises. The rest is minor.

What I checked against: the working-tree `FormModal.vue` (with S006's
`saveLabel`), `useFormModal.js`, `useMasterForm.js`, `ActiveToggle.vue`, all
ten dialogs, `PhotoViewer.vue`, Bootstrap 5.3.8's `js/src/modal.js` in
`node_modules`, `tooling/build/nginx.conf`, the devops `deploy.yaml`,
`compose.yml.j2`, `docs/lob-apps/Yantra.MD`, the sibling `geo/` and `oneerp/`
deploys (for the `docker_compose_v2` options), `Plan.MD`, the base § Form /
Modal Pattern, and the frontend test setup (`vite.config.js`, `tests/`).

## Findings

### BR1-01 (major) — Bootstrap still handles Esc with `keyboard: false`; it shakes the dialog and takes the focus

**Problem.** § 5.1 says "Bootstrap's own Esc is off with `keyboard: false`"
and that focus moves to **Keep editing**. In Bootstrap 5.3.8 (`modal.js`
lines 207–218) the keydown listener is always installed; with `keyboard:
false` it does not hide but calls `_triggerBackdropTransition()` — the same
routine as the outside-click "bounce". That routine (lines 264–289) fires
`hidePrevented.bs.modal`, adds the `modal-static` shake and ends with
`this._element.focus()`.

The brief's `@keydown` handler sits on the same root element. Vue binds
template listeners when the element is created, before `onMounted` creates the
`Modal` instance, so the brief's handler runs first and Bootstrap's second.
Net effect, per § 5.1 row:

- Esc on a changed form: the bar shows, focus goes to **Keep editing**, then
  Bootstrap shakes the dialog and moves focus to the modal root. The "safe
  choice has focus" promise is broken (Enter does nothing useful).
- Esc on an unchanged form: `hide()` starts, then the shake runs on a hiding
  modal (harmless but visibly odd).
- Esc while the bar shows: Keep editing, plus a shake.
- Outside click while the bar shows: shake and focus to the root — minor, but
  the same cause.

**Why it matters.** The coder would discover this mid-implementation and pick
a fix alone; § 5.1 is the contract the manual checks test against.

**Options.**

1. **Use Bootstrap's `hide.bs.modal` as the single gate (recommended).** Keep
   `backdrop: 'static'` but leave `keyboard: true`. Every close — Esc, ✕,
   Cancel (which can keep `data-bs-dismiss`), and `close()` — then passes
   through `hide()`, which fires a cancellable `hide.bs.modal` first
   (`modal.js` lines 123–132). One listener in `FormModal`: if `saving` →
   `preventDefault()`; else if the bar is showing → hide the bar,
   `preventDefault()` (Esc = Keep editing); else if `dirty` and not
   `allowHide` → `preventDefault()`, show the bar, focus Keep editing.
   `close()` and **Discard** set `allowHide = true` around their `hide()`.
   Bootstrap never shakes or re-focuses on this path, because `hide()` returns
   before doing anything when the event is prevented. This also makes the
   rejected alternative in § 7 ("harder to tell a save-close from a user
   close") a one-flag matter, so that row should change.
2. **Keep the brief's `requestClose()` and silence Bootstrap.** Listen for
   `hidePrevented.bs.modal` and `preventDefault()` it when the preceding
   keydown was an Esc the handler consumed (a flag set in the keydown handler,
   cleared on the next tick); outside clicks keep their shake. Works, but two
   listeners cooperate through a flag.
3. `event.stopImmediatePropagation()` in the keydown handler. Relies on Vue's
   listener being registered before Bootstrap's — true today, implicit, and
   fragile if `getOrCreateInstance` ever moves.

Whichever is chosen, § 5.1 should state it, and the "Esc" bullet should be
corrected.

### BR1-02 (minor) — `UserUnitsPanel`: the dialog is re-filled by code after open

**Problem.** § 5.2 asks the coder to list automatic changes after open and
re-snapshot through `markClean()`. `UserUnitsPanel.save()` has one that is
not a watcher or a load: when "Add user" is saved for a username that already
has access, it calls `load(existing.username, existing.units, false)` and
shows "their current units are shown. Review and save." The dialog now shows
the server's record, but the snapshot from `open('', [], true)` makes it look
changed, so Cancel asks "Discard your changes?" when nothing of the user's is
left to lose.

**Why it matters.** The brief's own rule: ask only when there is something to
lose. `UserUnitsPanel` computes its own `dirty`, so the coder has to decide
this alone unless the brief says.

**Options.** (a) Re-take the panel's snapshot after that `load(...)`
(recommended; one line). (b) Accept the extra question and say so in § 5.2.

### BR1-03 (minor) — Deactivate / Reactivate closes a changed dialog without asking

**Problem.** In the four masters dialogs, `ActiveToggle` → `changeActive()` →
`base.send()` → `finish()` → `modal.close()`. `close()` bypasses the guard by
design. Edits typed in the other fields are dropped (documented in
`useMasterForm.js`: "other unsaved edits in the dialog are not sent").
Deactivate is confirmed with Yes/No; Reactivate is one click. § 8's acceptance
("no form dialog loses typed input to … an unconfirmed …") does not say
whether this path is included.

**Why it matters.** It is the one remaining way to lose typed input with a
single click, and the base rule is written as an absolute.

**Options.** (a) State in § 1 "out of scope" that the active toggle is its
own action and keeps the existing behaviour (recommended; the user has pressed
a labelled button, and routing it through the guard would mean a second
question). (b) Disable the toggle while `dirty`, with a `title` saying why
("Save or discard your changes first").

### BR1-04 (minor) — § 5.4's reason for "recreate, not restart" is not right; the task is still right

**Problem.** § 5.4 says a restarted container "keeps the old" file. The
stale-inode problem is real while a container keeps running: Ansible's
`template` writes a temp file and renames it, so the bind mount (an inode)
still shows the old content. But Docker sets bind mounts up at every container
*start*, so `docker compose restart backend worker` re-binds the path and
would pick the new file up too. The claim "Recreating is what fixed it" is
true; "restart would not" is not established.

**Why it matters.** The YAML comment and the brief teach the project owner a
Docker fact; it should be the correct one. The choice itself is fine.

**Options.** (a) Keep `recreate: always` (proven on 15-10-2026, and it also
applies any other pending change) and reword the reason: "the mount is
re-bound only when the container starts; recreating is the proven, simplest
way" (recommended). (b) `state: restarted` with the same `services` — a
little faster, untested here.

Two related notes for the same section, both acceptable as-is but worth a
sentence: on a first deploy, and on any deploy where `docker compose up`
already recreated the backend for a new image, `secrets_file.changed` is true
and the new task recreates backend and worker a second time (a redundant
~35 s stop/start, bounded by `stop_grace_period`). Not worth a condition on
`compose_result`.

### BR1-05 (minor) — ISO 9241-110 principle name

**Problem.** § 2 cites "ISO 9241-110:2020, 'use error tolerance'". The 2006
edition called the principle *error tolerance*; the 2020 revision renamed it
**use error robustness** (the other six: suitability for the user's tasks,
self-descriptiveness, conformity with user expectations, learnability,
controllability, user engagement). The argument is the right one; the label
mixes the editions.

**Why it matters.** The project owner is learning the standards from these
briefs; the names should be the ones in the current text.

**Options.** Cite "ISO 9241-110:2020 § 'use error robustness' (called 'error
tolerance' in the 2006 edition)". In plain terms: the system should make
slips hard to commit and, when one happens, cheap to undo — exactly what the
static backdrop (hard to commit) and the Keep editing bar (cheap to undo) do.

The other citations are correct: Nielsen #5 *Error prevention*; ISO
27001:2022 A.8.9 *Configuration management* (configurations are established,
documented, implemented, monitored and reviewed — the running container must
match the deployed file); A.8.32 *Change management* (changes follow a
defined, repeatable procedure — the two manual steps become playbook tasks).
The statement that no maintenance standard is touched is right.

### BR1-06 (nit) — Define `dirty` before the snapshot exists

`openCreate`/`openEdit` take the snapshot in `nextTick`; between the call and
that tick `snapshot` is the previous dialog's or unset. State that `dirty` is
`false` while `snapshot === null`, and that `openCreate`/`openEdit` set it to
`null` before scheduling the new snapshot. No user can press Esc in that
window, but the rule should be explicit and the computed should not compare
against a stale snapshot.

### BR1-07 (nit) — `formSnapshot` details the coder would otherwise choose

- "sorted values" of a `Set`: say "with a fixed comparator" (default `sort()`
  orders numbers as strings — deterministic, so fine, but say it is only for
  a stable string, not for ordering).
- `JSON.stringify` drops `undefined` values, so `{a: undefined}` and `{}` are
  equal. The forms use `""` and `null`, so this is harmless; note it in the
  helper's comment.
- `File` detection with `instanceof File` works on the reactive form: Vue
  does not proxy `File` (not a plain object or collection), and a reactive
  `Set` proxy still passes `instanceof Set` and spreads correctly.

### BR1-08 (nit) — Two small spec gaps

- Name the test file's path: `frontend/tests/formSnapshot.test.js`, next to
  the existing tests (vitest's default include finds it; `vite.config.js`
  sets `environment: "jsdom"`, so `File` exists).
- "While saving, Esc, ✕ and Cancel do nothing": also `:disabled="saving"` on
  ✕ and Cancel, so a no-op is visible rather than silent.

### BR1-09 (nit) — Focus after Keep editing

When the bar hides, the focused button disappears and focus falls to `body`;
Bootstrap's focus trap pulls it back to the modal root on the next `focusin`.
Nicer and cheap: remember `document.activeElement` in `requestClose()` (or the
`hide.bs.modal` listener) and restore it on Keep editing, so the user is back
in the field they were typing in.

## Checked and found consistent

- **The ten dialogs and their open paths** (the § 5.2 timing). All fill the
  form synchronously before or right after `modal.open()`; none changes it
  after the next tick:
  - Sites, Units, Classes, Types: `blank()`/`fromRecord()` inside
    `useFormModal.openCreate/openEdit`; nothing after.
  - Equipment create: `open()` awaits the stores *before* `openCreate()`, then
    sets `form.unit_id` synchronously (the one-unit case the brief names) —
    inside the same tick, so a `nextTick` snapshot covers it. Class `@change`
    clearing `type_id` is a user action.
  - Move: awaits before `openEdit()`; the search box is outside `form`, so it
    is not a change, as § 1 says; `choose()` sets `parent_id` (a change).
  - Status: the scrap "No" button sets `form.status = node.status`, which the
    by-value comparison reads as unchanged — correct.
  - Upload: the `watch(() => form.value.kind, clearFile)` runs pre-flush on
    open only if the kind differs from the last open, and sets `file` from
    `null` to `null` — no change; the title pre-fill is driven by the user's
    file choice, as the brief says.
  - Title: `openEdit(doc)`, synchronous.
  - Unit access: `open()` → `load()` → `modal.open()`; the one later re-fill
    is BR1-02.
- **`PhotoViewer.vue`** uses its own `Modal` instance, not `FormModal`, so it
  keeps closing on an outside click, as § 1 says.
- **FormModal's S006 diff** is only `saveLabel` (`git diff -w HEAD`); the
  dependency on S006 being committed is right, and `data-bs-dismiss` is on ✕
  and Cancel today, so removing it (or keeping it under option 1 of BR1-01)
  is correctly listed.
- **Bootstrap static backdrop**: outside click → `_triggerBackdropTransition`
  → shake (`modal-static`) and `hidePrevented.bs.modal`; the brief's "bounce
  is kept" is accurate.
- **Nginx**: `resolver 127.0.0.11 valid=10s ipv6=off;` is valid syntax;
  `127.0.0.11` is Docker's embedded DNS on user-defined networks (compose
  creates one); `set` needs only the stock rewrite module; `proxy_pass` with
  a variable and no URI part passes the request URI unchanged, which is also
  what the current `proxy_pass http://backend:5000;` does; without a
  `resolver` a variable `proxy_pass` fails with "no resolver defined", so the
  pair is required together; the "no longer refuses to start" side effect is
  real. `nginx -t` does not resolve names, so the local check works.
- **Deploy**: `docker_compose_v2` with `project_src`, `files`, `services` and
  `recreate: always` is already used in `erp_server/geo/deploy.yaml` and
  `erp_server/oneerp/deploy.yaml` in the same repo, so the options are known
  to work with the installed collection. `frontend`'s `depends_on: backend`
  does not recreate the frontend when backend is recreated — hence Part B
  item 4 is needed, as the brief says. Placing the new task after
  `docker compose up` and before the health check is right; the health check
  (24 × 5 s) outlasts `stop_grace_period: 35s`.
- **`Yantra.MD` step 5**: it says `vel-yantra`; `Plan.MD` (login row and
  decision of 12-10-2026) and `backend/example_secrets_app.py` say
  `vel-yantra-master`. The correction is right.
- **Existing tests**: the five frontend test files (`appVersion`, `datetime`,
  `equipmentLabels`, `format`, `navigation`) touch nothing in Part A; no
  backend change. Nothing breaks.
- **Plan.MD**: nothing in phase 1/2 decisions conflicts; the deploy path
  (`erp_spanner.py deploy vel yantra master`) is unchanged.
- **Base pattern**: the guard is implemented once in `FormModal`, the change
  detection once in `useFormModal`, with one `:dirty` binding per dialog —
  consistent with "Implement this once, in the shared form-modal component".
  No `@vue/test-utils`; the decision to test only the pure helper is stated.
- **Scope**: nothing beyond the two fixes; the devops-repo question (§ 9.1)
  is correctly left to the user.
