```
Step: S007 — Dialog close guard; Nginx and deploy fixes
Doc: impl-report
Author: Coder (Sonnet)
Date: 16-10-2026
```

# S007 — Implementation report

## 1. What was built

**A. Dialog close guard** on all ten `FormModal` dialogs.
- A click outside never closes a form dialog (static backdrop).
- Esc, ✕ and Cancel close it at once when nothing changed; when something changed, the footer becomes "Discard your changes?" with **Keep editing** and **Discard**.
- Save behaviour is unchanged. While a save is in flight, Esc, ✕ and Cancel do nothing.

**B. Nginx and deploy fixes.**
- Nginx re-resolves `backend` through Docker's DNS per request (cached 10 s).
- The Ansible deploy recreates backend and worker when `secrets_app.py` changed.
- `Yantra.MD` step 5 names the client `vel-yantra-master`.

## 2. How it works

- **`formSnapshot(value)`** (pure): `JSON.stringify` with a replacer. A `File` becomes `file:<name>:<size>:<lastModified>`, a `Set` becomes a sorted array.
- **`useFormModal`:**
  - `snapshot` starts as `null`. `openCreate` / `openEdit` go through a small internal `open()` that sets it to `null`, opens the modal and calls `markClean` in `nextTick`.
  - `dirty` is `false` while the snapshot is `null`, otherwise `formSnapshot(form) !== snapshot`.
  - `dirty` and `markClean` are returned. `useMasterForm` passes `dirty` through.
- **`FormModal`:**
  - The Bootstrap modal is created with `{ backdrop: "static" }`. `keyboard` stays `true`.
  - **One gate:** `onHide` is attached with `addEventListener("hide.bs.modal")` in `onMounted` and removed in `onBeforeUnmount`. It decides in the brief's order:
    1. `allowHide` set: let it close.
    2. `saving`: prevent.
    3. The bar is showing (so this is Esc): prevent and hide the bar.
    4. `dirty`: prevent and show the bar.
    5. Otherwise: let it close.
  - `close()` and Discard call `hideNow()`, which sets `allowHide` around `modal.hide()` in `try`/`finally`.
  - The bar replaces the whole footer, so the `footer-left` slot is hidden too. Its two buttons are `type="button"`. `onSubmit` does nothing while the bar shows.
  - ✕ is disabled while `saving || confirming`. Cancel is disabled while `saving`.
  - **Focus:**
    - The bar remembers `document.activeElement`, then focuses **Keep editing** in `nextTick`.
    - Keep editing returns the focus to the remembered element in `nextTick`.
    - Both fall back to the dialog element (`tabindex="-1"`) when the focus ended up outside it.
  - `open()` hides the bar.
- **`UserUnitsPanel`** has its own `snapshot`, `dirty` and `markClean` over `{username, selected}`. `markClean` runs in `nextTick` after `open()`, and again after `save()` re-fills the dialog with an existing user's units.
- **Nginx:** `resolver 127.0.0.11 valid=10s ipv6=off;`, then `set $backend_upstream http://backend:5000; proxy_pass $backend_upstream;`. The rest of the block is unchanged.
- **Deploy:** `register: secrets_file` on the template task. A new task after "docker compose up" recreates `backend` and `worker` with `recreate: always`, `when: secrets_file.changed`. The YAML comment is as in the brief.

### Automatic form changes after open (brief § 5.2)

| Dialog | Change after open | Handling |
|---|---|---|
| Sites, Units, Equipment classes, Equipment types (masters) | None. `blank()` and `fromRecord` run inside `openCreate` / `openEdit`. The units default site comes from `blank`. | Snapshot in `nextTick` covers it. |
| Equipment create | `openCreateEquipment` sets `form.unit_id` (single pickable unit) synchronously after `openCreate`. `siteId` is set there too. | Same tick, so the `nextTick` snapshot includes it. No `markClean` needed. |
| Equipment create-part, Equipment edit | None. The loads are awaited before `prepare()` runs. | None needed. |
| Equipment move, Equipment status, Title | None. | None needed. |
| Upload | The `watch(form.kind)` runs `clearFile` when the seeded kind differs from the previous open. It sets `file` to `null`, which is already `null`. `fileInputKey += 1` is not in the form. The title pre-fill comes from the user choosing a file, so it counts as a change (per the brief). | Covered by the `nextTick` snapshot. |
| Unit access | `save()` re-fills via `load()` for an existing user. | Re-snapshot with `nextTick(markClean)` after `load()`. |

Equipment create: `siteId` lives outside `form`, so choosing only a site and nothing else does not count as a change. It is one click, and the unit choice (in `form`) does count.

## 3. Files touched (21)

Frontend, new:
- `frontend/src/utils/formSnapshot.js`: the pure snapshot helper.
- `frontend/tests/formSnapshot.test.js`: 7 tests (equal values, changed values, undo, `File`, `Set`, nested values, `undefined`).

Frontend, changed:
- `frontend/src/components/FormModal.vue`: the gate, `dirty` prop, static backdrop, confirm bar, focus handling, submit guard.
- `frontend/src/composables/useFormModal.js`: `snapshot`, `dirty`, `markClean`, internal `open()`.
- `frontend/src/views/masters/useMasterForm.js`: returns `dirty`.
- `frontend/src/views/masters/SitesPanel.vue`: `:dirty`.
- `frontend/src/views/masters/UnitsPanel.vue`: `:dirty`.
- `frontend/src/views/masters/EquipmentClassesPanel.vue`: `:dirty`.
- `frontend/src/views/masters/EquipmentTypesPanel.vue`: `:dirty`.
- `frontend/src/views/masters/UserUnitsPanel.vue`: own dirty, re-snapshot after the re-fill.
- `frontend/src/views/equipment/EquipmentFormModal.vue`: `:dirty`.
- `frontend/src/views/equipment/EquipmentMoveModal.vue`: `:dirty`.
- `frontend/src/views/equipment/EquipmentStatusModal.vue`: `:dirty`.
- `frontend/src/views/equipment/DocumentUploadModal.vue`: `:dirty`.
- `frontend/src/views/equipment/DocumentTitleModal.vue`: `:dirty`.

Nginx:
- `tooling/build/nginx.conf`: resolver and variable `proxy_pass`.

Docs:
- `docs/steps/S007-dialog-guard-deploy-fixes/1-brief.md`: status set to `In code review`.
- `docs/steps/README.md`: the S007 index row set to `In code review`.
- `docs/steps/S007-dialog-guard-deploy-fixes/3-impl-report.md`: this file.

Sibling repo `smtw_erp_devops` (working tree, **uncommitted**, per § 9.1 (a)):
- `erp_server/yantra/deploy.yaml`: `register: secrets_file` and the recreate task.
- `docs/lob-apps/Yantra.MD`: step 5, client `vel-yantra-master`.

Total: 19 files in Yantra (3 new including this report, 16 changed) and 2 in `smtw_erp_devops`.

## 4. Decisions taken

- `useFormModal` gained one small internal `open()` (set the snapshot to `null`, open the modal, `nextTick(markClean)`), so `openCreate` and `openEdit` don't repeat it. It is not exported.
- `FormModal`'s `close` is exposed as `hideNow`, which sets and clears `allowHide`. Discard uses the same function. This follows the brief.
- The confirm bar is a second `modal-footer` div under `v-if="confirming"` / `v-else`, so the normal footer and its slot are not rendered while the bar shows.
- The `formSnapshot` Set comparator is named `numericOrTextOrder` and is a plain `<`/`>` comparison. Unit ids are numbers, so this is stable.
- The "Keep editing" button is `btn-primary` and "Discard" is `btn-outline-danger`. The brief does not name styles.

No departures from the brief.

## 5. Not done, deferred, assumed

- **No component test for `FormModal`** (decided in the brief § 7). The close behaviour needs the manual checks in brief § 8 in a browser. **None were run by me**, so every one of them is still open, in particular Esc after the bar, Enter in a one-field dialog, the focus returning to the field, and the phone tap outside.
- **Nginx:** `nginx -t` on the repo's `nginx.conf` with `nginx:alpine` passed ("syntax is ok", "test is successful"). No image was built or pushed.
- **Deploy:** the Ansible change is not run or linted (no `ansible-lint` here). It follows the brief's YAML and should be checked on the real deploy (brief § 8, production checks).
- `smtw_erp_devops` is left uncommitted in its working tree. Before this step it had no other changes.
- The `redundant second recreate` on a first deploy is accepted in the brief.

## Test results

- `tooling/run-tests.bat`: backend **660 passed** (dev DB was up), frontend **36 passed** in 6 files (7 new).
- `npx vite build` in `frontend/`: built, no errors.
