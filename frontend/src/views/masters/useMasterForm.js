/**
 * Create/edit/deactivate logic shared by the masters panels.
 *
 * A panel supplies the REST path, a blank form, how to fill the form from a
 * record, and a reload callback; it gets back the modal state and handlers.
 * Validation and rules live in the backend — errors arrive as {error, field}
 * and are shown beside the field, or in the modal when no field is named.
 *
 * Deactivate / reactivate live in the edit dialog. They act at once with their
 * own PUT {active}; other unsaved edits in the dialog are not sent.
 */

import { computed, ref } from "vue";
import { apiPost, apiPut } from "../../api";
import { resetMasters } from "../../stores/masters";

export function useMasterForm({ path, blank, fromRecord, reload }) {
  const modal = ref(null); // template ref to <FormModal>
  const form = ref(blank());
  const editingId = ref(null);
  const editingActive = ref(true);
  const editingLabel = ref(""); // what the deactivate confirmation names, e.g. SMTW-KP
  const confirmingDeactivate = ref(false);
  const saving = ref(false);
  const error = ref(null); // {field, message} from the last refused save or activation change

  const fieldError = (name) => (error.value?.field === name ? error.value.message : "");
  // A refusal about a field the form does not show still has to be seen
  const modalError = computed(() =>
    error.value && !(error.value.field in form.value) ? error.value.message : ""
  );

  function openCreate() {
    editingId.value = null;
    form.value = blank();
    error.value = null;
    confirmingDeactivate.value = false;
    modal.value.open();
  }

  function openEdit(record) {
    editingId.value = record.id;
    editingActive.value = Boolean(record.active);
    editingLabel.value = record.full_code ?? record.code;
    form.value = fromRecord(record);
    error.value = null;
    confirmingDeactivate.value = false;
    modal.value.open();
  }

  async function finish() {
    modal.value.close();
    resetMasters();
    await reload();
  }

  async function save() {
    saving.value = true;
    error.value = null;
    try {
      if (editingId.value === null) await apiPost(path, form.value);
      else await apiPut(`${path}/${editingId.value}`, form.value);
    } catch (err) {
      error.value = { field: err.field, message: err.message };
      return;
    } finally {
      saving.value = false;
    }
    await finish();
  }

  async function changeActive(active) {
    saving.value = true;
    error.value = null;
    confirmingDeactivate.value = false;
    try {
      await apiPut(`${path}/${editingId.value}`, { active });
    } catch (err) {
      error.value = { field: err.field, message: err.message };
      return;
    } finally {
      saving.value = false;
    }
    await finish();
  }

  return {
    modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving,
    fieldError, modalError, openCreate, openEdit, save, changeActive,
  };
}
