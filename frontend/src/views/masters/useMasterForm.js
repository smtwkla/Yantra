/**
 * Create/edit/deactivate logic shared by the masters panels: useFormModal plus
 * the masters-only state and actions.
 *
 * Deactivate / reactivate live in the edit dialog. They act at once with their
 * own PUT {active}; other unsaved edits in the dialog are not sent.
 */

import { ref } from "vue";
import { apiPut } from "../../api";
import { useFormModal } from "../../composables/useFormModal";
import { resetMasters } from "../../stores/masters";

export function useMasterForm({ path, blank, fromRecord, reload, label, toBody }) {
  const editingActive = ref(true);
  const confirmingDeactivate = ref(false);

  // A saved master can change the codes shown elsewhere (a renamed site), so the shared cache is dropped
  const base = useFormModal({
    path,
    blank,
    fromRecord,
    label,
    toBody,
    afterSave: async () => {
      resetMasters();
      await reload();
    },
  });

  function openCreate() {
    confirmingDeactivate.value = false;
    base.openCreate();
  }

  function openEdit(record) {
    editingActive.value = Boolean(record.active);
    confirmingDeactivate.value = false;
    base.openEdit(record);
  }

  function changeActive(active) {
    confirmingDeactivate.value = false;
    return base.send(() => apiPut(`${path}/${base.editingId.value}`, { active }));
  }

  // send: for a dialog whose save is more than one request (the Team dialog's site rows, S011)
  const { modal, form, editingId, editingLabel, saving, dirty, fieldError, modalError, save, send } = base;
  return {
    modal, form, editingId, editingActive, editingLabel, confirmingDeactivate, saving, dirty,
    fieldError, modalError, openCreate, openEdit, save, send, changeActive,
  };
}
