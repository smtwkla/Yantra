/**
 * Create/edit logic for a form in a FormModal — the generic part shared by the
 * masters panels (through useMasterForm) and the equipment dialogs.
 *
 * The caller supplies the REST path, a blank form (seeded at open time), how to
 * fill the form from a record, and what to do after a save. Validation and rules
 * live in the backend: a refusal arrives as {error, field} and is shown beside
 * the field. Every field a dialog sends must therefore render fieldError(name)
 * somewhere, read-only ones included; a refusal for a field that is not in the
 * form is shown at the top of the dialog instead (modalError).
 */

import { computed, nextTick, ref } from "vue";
import { apiPost, apiPut } from "../api";
import { formSnapshot } from "../utils/formSnapshot";

// label(record) names the record being edited (a confirmation shows it); records without a code pass their own
const codeLabel = (record) => record.full_code ?? record.code;

export function useFormModal({ path, blank, fromRecord, afterSave, toBody = (form) => form, label = codeLabel }) {
  const modal = ref(null); // template ref to <FormModal>
  const form = ref(blank());
  const editingId = ref(null);
  const editingLabel = ref(""); // what a confirmation names, e.g. SMTW-KP
  const saving = ref(false);
  const error = ref(null); // {field, message, status} from the last refused save

  // The form as it was once the dialog was filled; null until then. `dirty` tells FormModal
  // whether closing would lose typed input.
  const snapshot = ref(null);
  const dirty = computed(() => snapshot.value !== null && formSnapshot(form.value) !== snapshot.value);

  // Taken in nextTick: a dialog may adjust the form right after opening it (a preselected
  // unit), and that must not make an untouched dialog look changed.
  function markClean() {
    snapshot.value = formSnapshot(form.value);
  }

  function open() {
    snapshot.value = null; // never compare with the previous dialog's snapshot
    modal.value.open();
    nextTick(markClean);
  }

  const fieldError = (name) => (error.value?.field === name ? error.value.message : "");
  const modalError = computed(() =>
    error.value && !(error.value.field in form.value) ? error.value.message : ""
  );

  function openCreate(seed) {
    editingId.value = null;
    editingLabel.value = "";
    form.value = blank(seed);
    error.value = null;
    open();
  }

  function openEdit(record) {
    editingId.value = record.id;
    editingLabel.value = label(record);
    form.value = fromRecord(record);
    error.value = null;
    open();
  }

  // Closes the modal first, then hands the API's response to afterSave, so the
  // modal is not left open over whatever afterSave opens.
  async function finish(result) {
    modal.value.close();
    await afterSave(result);
  }

  async function send(request) {
    saving.value = true;
    error.value = null;
    let result;
    try {
      result = await request();
    } catch (err) {
      error.value = { field: err.field, message: err.message, status: err.status };
      return;
    } finally {
      saving.value = false;
    }
    await finish(result);
  }

  function save() {
    const body = toBody(form.value);
    return send(() => (editingId.value === null ? apiPost(path, body) : apiPut(`${path}/${editingId.value}`, body)));
  }

  return {
    modal, form, editingId, editingLabel, saving, error, dirty, markClean,
    fieldError, modalError, openCreate, openEdit, save, send,
  };
}
