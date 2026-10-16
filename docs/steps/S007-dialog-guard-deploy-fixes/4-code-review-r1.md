```
Step: S007 — Dialog close guard; Nginx and deploy fixes
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S007 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** Two `nit`s, both optional.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: backend **660 passed**, frontend **36 passed** in 6 files
  (`formSnapshot.test.js`: 7 new), exit code 0.
- `npx vite build` in `frontend/`: built in 1.9 s, no errors or new warnings.
- `nginx -t` on `tooling/build/nginx.conf` with `nginx:alpine` (read-only mount, no image
  built): "syntax is ok", "test is successful".
- The Ansible change was not run or linted (no target). It was read against the brief.

## Findings

### CR1-01 — nit — `frontend/src/components/FormModal.vue:67-70`, `:124-131` — after Cancel, Keep editing returns the focus to the dialog, not the field

**Problem.** `askToDiscard()` remembers `document.activeElement`. When the bar is opened with
**Cancel**, the remembered element is the Cancel button. The footer is swapped with
`v-if="confirming"` / `v-else`, so on Keep editing Vue renders a *new* Cancel button. The
remembered one is detached, `el.contains()` fails, and the focus falls back to the dialog
itself. With ✕, the focus goes back to ✕.

This is what the brief literally says (§ 5.1: back to "the element that had it", else the
dialog). Esc, the case in the § 8 manual check, does return to the field. So this is not a
departure from the brief.

**Scenario.** A user types a name, clicks Cancel and then Keep editing. The cursor is not in
the name field. They must click it or press Tab to go on typing.

**Suggested fix (optional).** When the remembered element is no longer in the dialog or is a
footer/header button, focus the dialog's first field (for example
`el.querySelector(".modal-body input, .modal-body select, .modal-body textarea")`) before the
dialog fallback. Or leave it as it is: the dialog fallback keeps Esc working, and that was the
point of BR2-04.

### CR1-02 — nit — `frontend/src/views/equipment/EquipmentFormModal.vue:117-128`; `3-impl-report.md` § 2 — the site picker is not part of the snapshot

**Problem.** In the equipment create dialog, `siteId` is a separate ref outside `form`. If the
user chooses only a site and closes, nothing is asked. The report states this, but in § 2
(How it works) rather than under § 4 "Decisions taken". The brief defines "changed" as
`formSnapshot(form)`, so this follows from the brief and is not a departure. It is still a
visible consequence, so it belongs in the user's view of the choices made.

**Scenario.** Add equipment → pick a site in a plant with several sites → Esc. The dialog
closes without asking. One click is lost, and nothing typed.

**Suggested fix.** No code change. In the report, add one line to § 4 so the user approves it
knowingly. Or include `siteId` in the snapshot input (`formSnapshot({ ...form, siteId })`)
through an optional extra-state argument to `useFormModal`, if the user wants it to count.

## Checked and found consistent

**FormModal against Bootstrap 5.3.8 `modal.js`** (`frontend/node_modules/bootstrap/js/src/modal.js`,
`dom/event-handler.js`, `util/component-functions.js`):
- **The event reaches the listener.** `EventHandler.trigger` dispatches a native
  `new Event("hide.bs.modal", { cancelable: true })` with `element.dispatchEvent`. The
  `addEventListener` gate receives it, and `hide()` checks `hideEvent.defaultPrevented` before
  it changes any state. The listener is attached in `onMounted` and removed in
  `onBeforeUnmount`, not as a template `@hide.bs.modal` (BR2-01).
- **The gate order matches § 5.1:** `allowHide`, then `saving`, then `confirming` (Esc = Keep
  editing), then `dirty`, else close.
- **`allowHide` in `try`/`finally`.** `hide()` returns early, without the event, when
  `!_isShown || _isTransitioning`. The flag is cleared in `finally`, so it never stays set on
  an open dialog (BR2-05). Because `hide()` fires the event synchronously, the flag is still
  set when `onHide` reads it.
- **Esc and clicks.**
  - **Esc:** with `keyboard: true`, the `keydown.dismiss.bs.modal` handler on the `.modal`
    element calls `hide()`.
  - **Outside click:** `backdrop: "static"` routes it to `_triggerBackdropTransition()`. That
    shakes the dialog and focuses `this._element`; `hide()` is never called (BR2-06, accepted).
  - **✕ and Cancel:** they go through `enableDismissTrigger`. It returns early for disabled
    buttons, and in any case calls `getOrCreateInstance(target)`, which gets the existing
    instance with its static config.
- **Focus moves.**
  - Both moves run in `nextTick`, after the bar is rendered or removed.
  - `focusOrDialog` falls back to `el` (the `.modal`, `tabindex="-1"`), so the focus is never
    left on `<body>`, where Bootstrap's Esc listener would not hear it (BR2-04).
  - Esc after the bar: Esc with Keep editing focused bubbles to the `.modal` → `hide()` →
    step 3 → `keepEditing()` → the focus returns to the field. A third Esc shows the bar again.
- **Submit while the bar shows.**
  - Keep editing and Discard are `type="button"`.
  - `onSubmit` emits nothing while `confirming`.
  - The Save button is not rendered then (`v-else`), and neither is `footer-left`, which holds
    the masters' ActiveToggle.
  - Enter in a one-field dialog therefore cannot save past the bar (BR2-02).
- **Disabled buttons.** ✕ is disabled while `saving || confirming`, so step 3 is reached only
  by Esc (BR2-03). Cancel is disabled while `saving`.
- **Other.** `open()` resets `confirming`. `close()` is `hideNow`. The successful-save path
  (`useFormModal.finish` → `modal.close()`) and `UserUnitsPanel.save()` both pass the gate
  through `allowHide`. The text is "Discard your changes?" with `role="alert"`. No
  `confirm()` is used.

**Snapshot timing.**
- **When the snapshot is taken.** `useFormModal.open()` sets `snapshot = null` before
  `modal.open()`, so `dirty` is `false` until the snapshot exists. It then calls
  `nextTick(markClean)`. Vue 3's `nextTick` chains on `currentFlushPromise`, which is already
  set because replacing `form.value` and `snapshot` queued jobs. `markClean` therefore runs
  after the pre-flush watchers.
  - `DocumentUploadModal`'s `watch(form.kind, clearFile)`, `null` → `null`, is included.
  - `EquipmentFormModal`'s synchronous `form.unit_id` preselect (single pickable unit) is
    included.
- **No later automatic change was found.**
  - `EquipmentFormModal` and `EquipmentMoveModal` await their loads *before* calling
    `openCreate` / `openEdit`. The move dialog's `error` and `search` are outside `form`.
  - The masters' defaults (`blank()` with the site/class filter) are synchronous.
  - The coder's table in report § 2 matches what I found.
- **`UserUnitsPanel`.**
  - It has its own `snapshot` / `dirty` / `markClean` over `{username, selected}`, with the
    same helper. The brief allows this in § 3.
  - `snapshot` is set to `null` before `open()`, and `nextTick(markClean)` follows.
  - After the existing-user re-fill in `save()`, `nextTick(markClean)` runs (BR1-02). The
    error set after it is not part of the snapshot.
  - `selected` is a reactive `Set`. `instanceof Set` holds on the proxy, and spreading uses the
    collection handlers' iterator.
- **The refused-save paths** keep the open-time snapshot, so the dialog stays dirty.

**`formSnapshot`.**
- It is pure, with no Vue imports.
- `File` → `file:name:size:lastModified`; Vue does not proxy a `File` (its target type is
  INVALID).
- `Set` → a sorted array.
- `undefined` is documented.
- The tests cover every § 8 item: equal, changed string/number/null, undo, `File`
  none/different/same, `Set` order and members, nested values, and `undefined`.

**Wiring.**
- All ten dialogs pass `:dirty`: sites, units, classes, types, unit access, equipment
  create/edit, move, status, upload and title.
- `useMasterForm` passes `dirty` through.
- `PhotoViewer.vue` is untouched and keeps its default backdrop.

**Nginx.**
- `resolver 127.0.0.11 valid=10s ipv6=off;` and `set $backend_upstream http://backend:5000;`
  are in `location /api/`, followed by `proxy_pass $backend_upstream;`. With no URI part, the
  request URI is passed as before.
- The other directives in the block are unchanged.
- The default `proxy_redirect` is lost with a variable `proxy_pass`, which is harmless here:
  the backend has no `redirect()` calls, and `Host` is passed as `$host`.

**Devops (`smtw_erp_devops`, uncommitted, § 9.1 (a)).**
- `deploy.yaml` has `register: secrets_file` on "Template secrets_app.py".
- After "docker compose up" it has the new task, word for word as in brief § 5.4:
  `docker_compose_v2`, services `backend` and `worker`, `recreate: always`,
  `when: secrets_file.changed`, and the corrected comment.
- `frontend` depends on `backend`, not the other way round, so it is not recreated. With the
  Nginx fix, it does not need to be.
- `Yantra.MD` step 5 now names `vel-yantra-master`. This matches `keycloak_client_id` in
  `vars/example_settings_vel_yantra_master.yaml`.
- No other file in the devops tree changed.

**Scope.**
- Nothing was built beyond the brief.
- `markClean` is returned from `useFormModal`, as § 3 asks, though no caller uses it yet.
- The report's "Decisions taken" covers:
  - the internal `open()`;
  - `hideNow`;
  - the `v-if` / `v-else` footer;
  - the comparator;
  - the button styles.

  None of them departs from the brief, apart from CR1-02's placement in the report.
- The rules: no backend change; no deprecated APIs; comments explain why; no swallowed errors
  (`hideNow` rethrows through `finally`).
- The README index edits to the S006 and S009 rows are status bookkeeping from other steps,
  not S007 code.

## Manual browser checks still open (user)

None of the brief § 8 manual checks has been run; the coder says so in report § 5. All are
still needed, in particular:
- In each of: Add site, Edit unit, Add equipment, Move, Status, Unit access, Upload (choose a
  file only), Edit title:
  - outside click → stays open;
  - Esc when untouched → closes;
  - type, Esc → the bar; Keep editing → the cursor is back in the field;
  - ✕ → the bar; Discard → closes; reopen → fresh;
  - Esc, Esc, Esc → bar, hidden, bar again (Esc still works after the bar);
  - Edit title / Unit access: type, Esc, Enter → nothing saved;
  - type and undo, Cancel → closes without asking;
  - valid Save → closes; a refused save → error, and Esc still asks.
- Unit access: "Add user" with an existing username → their units are shown; Cancel → closes
  without asking.
- Photo viewer: still closes on an outside click.
- Phone: a tap outside leaves the dialog open.
- Optional, for CR1-01: Cancel → Keep editing, and see where the cursor lands.

Production checks (user or devops, after the next deploy): `up -d --force-recreate backend`,
then `/api/version` → 200 within ~10 s with no frontend restart. On a deploy, the "recreate
backend and worker" task shows `changed` after a secrets change and `skipped` otherwise.
