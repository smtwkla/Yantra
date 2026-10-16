```
Step: S007 — Dialog close guard; Nginx and deploy fixes
Doc: brief
Author: Planner (Opus)
Date: 16-10-2026 (revised 16-10-2026 after brief-review r1)
Status: In code review
```

# S007 — Dialog close guard; Nginx and deploy fixes

Two small, unrelated fixes, both found by using the app (user, 16-10-2026):

- **A. Dialog close guard.** A create or edit dialog closes on a click outside
  it, and everything typed is lost. The rule is now in
  `.claude/SMTW-WebApp-Base.md` § Form / Modal Pattern ("Never lose typed
  input").
- **B. Nginx and deploy fixes.** On the first production deploy (15-10-2026):
  - recreating the backend container gave every API call **502** until the
    frontend was restarted by hand;
  - a changed `secrets_app.py` (the Keycloak client ID) was **not picked up**
    by the running backend, so login said "Client not found" until the
    containers were recreated by hand.

**Depends on:** S006 committed. Part A changes `FormModal.vue`, which S006
changes too (`saveLabel`), and covers S006's two new dialogs.

Background reading:
- `.claude/SMTW-WebApp-Base.md` § Form / Modal Pattern;
- `frontend/src/components/FormModal.vue`, `frontend/src/composables/useFormModal.js`,
  `frontend/src/views/masters/useMasterForm.js`;
- `frontend/src/components/ActiveToggle.vue` (the in-page confirmation precedent);
- `node_modules/bootstrap/js/src/modal.js` (`hide()`, `hide.bs.modal`, the
  static-backdrop and Esc handling);
- `tooling/build/nginx.conf`;
- `smtw_erp_devops/erp_server/yantra/deploy.yaml` and `compose.yml.j2`;
- `smtw_erp_devops/docs/lob-apps/Yantra.MD` § setup step 5.

## 1. What will be built

### A. Dialog close guard (every form dialog)

1. **A click outside a form dialog never closes it.**
2. **Esc, ✕ and Cancel** close it at once when nothing was changed. When
   something was changed, the footer turns into a question instead:
   *"Discard your changes?"* **[Keep editing]** **[Discard]**.
3. **Save** is unchanged: a successful save closes the dialog without asking;
   a refused save keeps it open with the error.

It applies to all ten dialogs built on `FormModal`: sites, units, equipment
classes, equipment types, unit access, equipment create/edit, move, status, and
S006's upload and title dialogs. The photo viewer is not a form and keeps
closing on an outside click.

### B. Nginx and deploy fixes

4. **Nginx finds the backend again by itself.** The frontend's Nginx looks up
   the backend's address through Docker's DNS at request time (cached 10 s),
   instead of once at start. Recreating the backend no longer needs a frontend
   restart.
5. **A changed `secrets_app.py` takes effect on deploy.** The Ansible deploy
   recreates the backend and worker containers whenever it rewrites
   `secrets_app.py`.
6. **The setup doc is corrected:** `Yantra.MD` step 5 names the real Keycloak
   client, `vel-yantra-master`.

**Out of scope:**
- guarding a page change or a closed browser tab while a dialog is open
  (`beforeunload`, router guards); the dialog is lost with the page, as now;
- the move dialog's search box: text typed there but not chosen isn't a change
  (cheap to retype); choosing a new parent is;
- **Deactivate / Reactivate** inside the masters dialogs: a labelled button the
  user presses on purpose (Deactivate already asks Yes/No). It keeps today's
  behaviour and closes the dialog, unsaved edits in other fields included
  (BR1-03);
- pinning the `nginx:alpine` base image to a version (a separate gap);
- any other change to the deploy (health check, image pull).

## 2. Standards and practice

None of the maintenance standards (TPM, ISO 14224, EN 13306, ISO 55000) is
touched: this step is about the tool, not about maintenance practice.

- **ISO 9241-110:2020 (interaction principles), "use error robustness"**
  (called "error tolerance" in the 2006 edition). The system should make slips
  hard to commit and, when one happens, cheap to undo. Here the static backdrop
  makes the slip hard to commit, and the Keep editing bar makes it cheap to
  undo. It asks only when there is something to lose, so the question stays
  rare and keeps its meaning (a question shown on every close is soon clicked
  through without reading).
- **Nielsen's heuristic 5, "error prevention".** The same idea: design the slip
  away rather than explain the loss afterwards.
- **ISO 27001:2022 A.8.9 (configuration management).** The configuration that
  is deployed must be the configuration that runs. A secrets file rewritten on
  disk but not read by the running container is exactly that kind of drift.
  Recreating the containers when the file changes closes it.
- **ISO 27001:2022 A.8.32 (change management)** asks that a change be applied
  in a controlled, repeatable way. The two manual steps of 15-10-2026
  (`restart frontend`, `up --force-recreate`) become part of the deploy.

## 3. Where

### Frontend (Part A)

- **`frontend/src/utils/formSnapshot.js`** (new, pure): `formSnapshot(value)`
  → a string that compares two forms (§ 5.2). Tests in
  `frontend/tests/formSnapshot.test.js`.
- **`frontend/src/components/FormModal.vue`:**
  - a `dirty` prop (Boolean, default `false`);
  - the Bootstrap modal created with `{ backdrop: "static" }` (`keyboard` stays
    `true`);
  - **one gate:** a listener on Bootstrap's cancellable `hide.bs.modal` event
    decides every close (§ 5.1). It is attached with
    `el.value.addEventListener("hide.bs.modal", onHide)` in `onMounted` and
    removed in `onBeforeUnmount`; **not** a template `@hide.bs.modal`, which Vue
    reads as an event named `hide` with modifiers, so the gate would never run
    (BR2-01). ✕ and Cancel keep `data-bs-dismiss`; Cancel gets
    `:disabled="saving"`, ✕ gets `:disabled="saving || confirming"` (BR2-03);
  - **no submit while the bar shows:** Keep editing and Discard are
    `type="button"` (inside the `<form>` they would otherwise submit), and the
    form's submit handler does nothing while the bar shows, so Enter in a
    one-field dialog can't save past it (BR2-02);
  - the confirm bar in the footer (§ 5.1);
  - `close()` (exposed, used after a successful save) and **Discard** set an
    `allowHide` flag, call `hide()`, and clear the flag right after it returns
    (`try`/`finally`): Bootstrap's `hide()` returns without firing the event
    while a transition is running, which would otherwise leave the flag set on
    an open dialog (BR2-05). `open()` hides the confirm bar.
- **`frontend/src/composables/useFormModal.js`:** a snapshot taken after the
  dialog has been filled, a `dirty` computed and `markClean()`, returned with
  the rest (§ 5.2).
- **`frontend/src/views/masters/useMasterForm.js`:** passes `dirty` through.
- **The ten dialogs:** `:dirty="dirty"` on `<FormModal>`.
  `UserUnitsPanel.vue`, which doesn't use `useFormModal`, computes its own
  `dirty` from its username and selected set, with the same helper. It re-takes
  its snapshot after `save()` re-fills the dialog with an existing user's units
  (BR1-02).

### Nginx (Part B, this repo)

- **`tooling/build/nginx.conf`**, `location /api/`:
  ```nginx
  # Docker's DNS, so a recreated backend container (new address) is found again
  resolver 127.0.0.11 valid=10s ipv6=off;
  set $backend_upstream http://backend:5000;
  proxy_pass $backend_upstream;
  ```
  Everything else in the block stays.

### Devops (Part B, the sibling repo `smtw_erp_devops`)

- **`erp_server/yantra/deploy.yaml`** (§ 5.4).
- **`docs/lob-apps/Yantra.MD`** step 5: the client is `vel-yantra-master`.

Who edits these is open question § 9.1.

### Docs

- `.claude/CLAUDE.md`: nothing (the rule already lives in `SMTW-WebApp-Base.md`).

## 4. Data model

None.

## 5. Rules

### 5.1 Closing a form dialog

| What the user does | Form unchanged | Form changed |
|---|---|---|
| Clicks outside the dialog | stays open | stays open |
| Esc, ✕, Cancel | closes | shows the confirm bar |
| **Keep editing** (or Esc while the bar shows) | — | hides the bar; the form is as it was |
| **Discard** | — | closes; the next open starts fresh, as now |
| Save, success | closes | closes |
| Save, refused | stays open with the error | stays open with the error |

- **How: one gate.** Every close goes through Bootstrap's `hide()`, which first
  fires the cancellable `hide.bs.modal` event. When the listener calls
  `preventDefault()`, Bootstrap stops there: no shake, no focus change. The
  listener decides, in this order:
  1. `allowHide` set (a save-close or Discard) → let it close;
  2. `saving` → prevent;
  3. the confirm bar is showing (so this is Esc) → prevent, hide the bar:
     Esc = Keep editing;
  4. `dirty` → prevent, show the bar;
  5. otherwise → let it close.
- With `keyboard: true`, Esc calls `hide()` and so passes the same gate. An
  outside click with the static backdrop never calls `hide()`: Bootstrap shakes
  the dialog slightly instead, which is kept as the feedback, and moves the
  focus to the dialog itself (accepted; a Tab returns to the fields) (BR2-06).
- ✕ is disabled while the bar shows, so step 3 of the gate is reached only by
  Esc (BR2-03).
- **While saving** (`saving` true): Esc, ✕ and Cancel do nothing, so a request
  in flight can't lose its dialog. ✕ and Cancel are disabled then, so the
  no-op is visible.
- **The confirm bar** replaces Cancel and Save in the footer (the
  `footer-left` slot is hidden too), so it can't be missed and Save can't be
  clicked past it. Focus moves to **Keep editing**, the safe choice. Text:
  "Discard your changes?" with `role="alert"`, so a screen reader announces it.
- **Keep editing** returns the focus to the element that had it before the bar
  showed (remembered by the gate), so the user is back in their field (BR1-09).
- **Both focus moves** (to Keep editing, and back) happen in `nextTick`, after
  the bar is rendered or removed, and fall back to the dialog itself:
  `if (!el.contains(document.activeElement)) el.focus()`. A removed focused
  button sends the focus to `body`, where Bootstrap's Esc listener (on the
  dialog) would not hear Esc; on iOS the remembered element may be `body`
  (BR2-04).
- **No browser `confirm()`**, following `ActiveToggle.vue` and the base rule.

### 5.2 What counts as a change

- `formSnapshot(value)`: `JSON.stringify` with a replacer that turns a `File`
  into `"file:<name>:<size>:<lastModified>"` (plain `JSON.stringify` writes a
  `File` as `{}`, so choosing a file wouldn't count) and a `Set` into an array
  sorted with a fixed comparator (only to make the string stable). Pure; no Vue
  imports. `instanceof File` and `instanceof Set` work on Vue's reactive form
  (a `File` isn't proxied; a reactive `Set` passes `instanceof`). Its comment
  notes that `undefined` values drop out (`{a: undefined}` equals `{}`); the
  forms use `""` and `null`, so this is harmless.
- `dirty` is `false` while `snapshot` is `null`. `openCreate` / `openEdit` set
  it to `null` first, so a dialog never compares with the previous one's
  snapshot.
- Otherwise `dirty` = `formSnapshot(form) !== snapshot`, where `snapshot` is
  taken **after** the dialog has been filled: in `nextTick` after `openCreate` /
  `openEdit`. Several dialogs adjust the form right after opening it (e.g. the
  equipment dialog picks the only unit); a snapshot taken before that would make
  an untouched dialog look changed.
- Changing a field and changing it back counts as unchanged (the comparison is
  by value, not "was touched").
- A refused save keeps the snapshot from the open, so the form stays changed.
- The coder checks every dialog for a later, automatic change to the form (a
  watcher, a load that finishes after `nextTick`, a re-fill by code) and lists
  each in the report. If one exists, its dialog re-takes the snapshot after it,
  through `markClean()`. The review found one: `UserUnitsPanel.save()` (§ 3).
  The upload dialog's title pre-fill comes from the user choosing a file, so it
  is a change, not a reset.

### 5.3 Nginx

- `resolver 127.0.0.11` is Docker's embedded DNS, present in every
  user-defined network (compose creates one). `valid=10s` caches an answer for
  10 s, so a recreated backend is found within 10 s; `ipv6=off` because the
  compose network is IPv4 only.
- `proxy_pass` with a variable makes Nginx resolve the name per request
  instead of once at start. With no URI part in the variable, the request URI
  is passed unchanged, as now. A variable `proxy_pass` needs the `resolver`;
  the two go together.
- A side effect, welcome: Nginx no longer refuses to start when `backend` can't
  be resolved at that moment; it answers 502 for that request instead.

### 5.4 The deploy

In `deploy.yaml`:
1. `register: secrets_file` on the "Template secrets_app.py" task.
2. After "docker compose up", a new task:
   ```yaml
   # A running container's single-file bind mount keeps showing the old file
   # after Ansible replaces it, and compose sees no config change: recreate.
   - name: recreate backend and worker after a secrets change
     community.docker.docker_compose_v2:
       project_src: "{{app_dir}}"
       files:
         - compose.yml
       services:
         - backend
         - worker
       recreate: always
     when: secrets_file.changed
   ```
3. The health check that follows stays as it is; with Part B item 4 it passes
   after the recreate without a frontend restart.

**Why:** Ansible writes the new file under a temporary name and renames it into
place, so it is a new file. A **running** container's bind mount of a single
file keeps showing the old one; the mount is re-bound only when the container
starts. A restart would therefore also work, but recreating is the fix proven
on 15-10-2026 and also applies any other pending change, so it is kept (BR1-04).

**Accepted:** on a first deploy, or when `docker compose up` already recreated
the backend for a new image, this task recreates backend and worker a second
time (a redundant stop/start of up to ~35 s). Not worth a condition.

## 6. API

None.

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Static backdrop, and a confirm only when changed | Removes the accidental case; asks only when there is something to lose (ISO 9241-110) | A confirm on every close (soon clicked through); static backdrop only (Esc still loses work) |
| The confirm in the dialog's footer | One modal, no stacking; follows `ActiveToggle` | Browser `confirm()`; a second modal on top |
| Changed = compare a snapshot by value | "Typed and undone" isn't a change; works for every dialog without per-field code | Tracking "touched" fields |
| Snapshot after `nextTick` | Dialogs set defaults right after opening | Snapshot inside `openCreate` |
| One gate on Bootstrap's cancellable `hide.bs.modal`; an `allowHide` flag for save-close and Discard | Esc, ✕ and Cancel all pass through `hide()`; Bootstrap does nothing else when it is prevented (BR1-01) | `keyboard: false` with an own Esc handler (Bootstrap then still shakes the dialog and takes the focus on Esc) |
| Nginx resolver + variable `proxy_pass` | Standard Nginx way to re-resolve a name; no deploy-order dependence | Restarting the frontend in every deploy (slower, still breaks on a manual backend recreate) |
| Recreate backend/worker on a secrets change | Matches the fix that worked; only when the file changed | Hashing the secrets into a compose label (puts a secrets hash in `docker inspect`); mounting a directory instead of the file (changes the image's paths) |
| No component tests for `FormModal` | Would need `@vue/test-utils`, a new dependency; the pure snapshot logic is tested, the clicks are a manual check | Adding `@vue/test-utils` |

## 8. Tests and acceptance

### Frontend (vitest, `frontend/tests/formSnapshot.test.js`)
- Same values → same snapshot; a changed string, number or `null` → different.
- Changed and changed back → same.
- A `File` (jsdom has `File`): none vs chosen → different; two different files
  → different; the same file → same.
- A `Set`: the same values in another order → same; one more → different.
- Nested objects and arrays.
- `undefined` vs absent → same (the documented behaviour).

### Backend
- None (no backend change). `tooling/run-tests.bat` stays green.

### Nginx
- The config passes `nginx -t`, checked locally with the same base image:
  `docker run --rm -v <repo>/tooling/build/nginx.conf:/etc/nginx/conf.d/default.conf:ro nginx:alpine nginx -t`
  (no image is built or pushed).

### Manual checks (user, dev)
- In each of: Add site, Edit unit, Add equipment, Move, Status, Unit access,
  Upload (choose a file only), Edit title:
  - open, click outside → stays open;
  - open, press Esc without typing → closes;
  - type something, press Esc → the bar; Keep editing → the text is still there
    and the cursor is back in the field; ✕ → the bar; Discard → closes; open
    again → empty (or the record's values);
  - type, Esc → the bar; Esc again → the bar hides; Esc once more → the bar
    again (Esc still works after the bar);
  - in Edit title or Unit access: type, Esc → the bar; press Enter → nothing is
    saved (Keep editing has the focus, so the bar hides);
  - type and delete it again, Cancel → closes without asking;
  - Save a valid form → closes without asking; a refused save → error, and Esc
    still asks.
- Unit access: Add user with the name of a user who already has access, Save →
  their units are shown; Cancel → closes without asking.
- The photo viewer still closes on an outside click.
- On a phone: tapping outside a dialog leaves it open.

### Manual checks (user or devops, production)
- After the next deploy: `docker compose up -d --force-recreate backend` on
  customer7, then within ~10 s `curl https://vel-yantra.mspv.app/api/version`
  → 200 with no frontend restart.
- A deploy with a changed secret (or a touched template) shows the "recreate
  backend and worker" task as `changed`; one without shows it `skipped`.

### Acceptance
- `tooling/run-tests.bat` green; `npx vite build` clean; `nginx -t` passes.
- No form dialog loses typed input to an outside click or an unconfirmed
  Esc / ✕ / Cancel.

## 9. Open questions and assumptions

1. **Decided (user, 16-10-2026) — (a):** the coder edits the
   `smtw_erp_devops` working tree (§ 5.4, `Yantra.MD`), uncommitted; the devops
   team reviews and commits.
2. **Confirmed (user, 16-10-2026):** Esc while the confirm bar is showing means
   "Keep editing" (the safe choice), not "Discard".
3. **Confirmed (user, 16-10-2026):** the confirm text is "Discard your
   changes?" for both create and edit.

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 16-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 Bootstrap still handles Esc with `keyboard: false` | major | **Accepted, option 1.** One gate on `hide.bs.modal`; `keyboard` stays `true`; `allowHide` for save-close and Discard; ✕ and Cancel keep `data-bs-dismiss` (§ 3, § 5.1, § 7). |
| BR1-02 `UserUnitsPanel` re-fills the dialog in `save()` | minor | **Accepted, (a).** Its snapshot is re-taken after that `load()`; a manual check (§ 3, § 5.2, § 8). |
| BR1-03 Deactivate / Reactivate closes a changed dialog | minor | **Accepted, (a).** Out of scope, stated: a deliberate labelled action keeps today's behaviour (§ 1). |
| BR1-04 "A restart keeps the old file" isn't right | minor | **Accepted, (a).** Recreate kept; the reason and the YAML comment corrected; the redundant second recreate accepted (§ 5.4). |
| BR1-05 ISO 9241-110 principle name | minor | **Accepted.** "Use error robustness" (2020), "error tolerance" (2006), with the plain-terms reading (§ 2). |
| BR1-06 `dirty` before the snapshot exists | nit | **Accepted.** `false` while `null`; reset on open (§ 5.2). |
| BR1-07 `formSnapshot` details | nit | **Accepted.** Fixed comparator; `undefined` noted; `instanceof` on reactive values (§ 5.2, § 8). |
| BR1-08 Test path; ✕ and Cancel while saving | nit | **Accepted** (§ 3, § 5.1, § 8). |
| BR1-09 Focus after Keep editing | nit | **Accepted.** Focus returns to the previous element (§ 5.1, § 8). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 16-10-2026

All nine round-1 answers verified in the text; the one gate verified against
Bootstrap 5.3.8. No blocker or major finding; the loop ends here, and the
answers below are not re-reviewed.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 A template `@hide.bs.modal` listens for `hide` | minor | **Accepted.** `addEventListener` in `onMounted`, removed on unmount (§ 3). |
| BR2-02 The form can be submitted while the bar shows | minor | **Accepted.** `type="button"` on both bar buttons; submit is a no-op while the bar shows; a manual check (§ 3, § 8). |
| BR2-03 ✕ reaches gate step 3 | minor | **Accepted.** ✕ disabled while the bar shows (§ 3, § 5.1). |
| BR2-04 Focus moves need `nextTick` and a fallback | minor | **Accepted.** Both in `nextTick`, falling back to the dialog; a manual check that Esc still works (§ 5.1, § 8). |
| BR2-05 Clear `allowHide` after `hide()` returns | nit | **Accepted.** `try`/`finally` (§ 3). |
| BR2-06 An outside click also moves the focus | nit | **Accepted.** Stated as accepted (§ 5.1). |

### Gate A — user decisions, 16-10-2026

- § 9.1 (a): the coder edits the devops working tree; the devops team commits.
- § 9.2 and § 9.3 confirmed.
- Coder: Sonnet (frontend UI on an existing pattern, small config edits).
- Approved by KLA. Coding starts after S006 is committed.
