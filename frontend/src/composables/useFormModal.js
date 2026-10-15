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

import { computed, ref } from "vue";
import { apiPost, apiPut } from "../api";

// label(record) names the record being edited (a confirmation shows it); records without a code pass their own
const codeLabel = (record) => record.full_code ?? record.code;

export function useFormModal({ path, blank, fromRecord, afterSave, toBody = (form) => form, label = codeLabel }) {
  const modal = ref(null); // template ref to <FormModal>
  const form = ref(blank());
  const editingId = ref(null);
  const editingLabel = ref(""); // what a confirmation names, e.g. SMTW-KP
  const saving = ref(false);
  const error = ref(null); // {field, message} from the last refused save

  const fieldError = (name) => (error.value?.field === name ? error.value.message : "");
  const modalError = computed(() =>
    error.value && !(error.value.field in form.value) ? error.value.message : ""
  );

  function openCreate(seed) {
    editingId.value = null;
    editingLabel.value = "";
    form.value = blank(seed);
    error.value = null;
    modal.value.open();
  }

  function openEdit(record) {
    editingId.value = record.id;
    editingLabel.value = label(record);
    form.value = fromRecord(record);
    error.value = null;
    modal.value.open();
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
      error.value = { field: err.field, message: err.message };
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
    modal, form, editingId, editingLabel, saving, error,
    fieldError, modalError, openCreate, openEdit, save, send,
  };
}
