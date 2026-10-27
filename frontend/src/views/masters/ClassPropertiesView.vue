<script setup>
/**
 * A class's properties (S043 § 7.2, U6): the table in the Classes panel, shown instead of the
 * class table as Models shows a model's Documents; Back brings the class table back.
 * Add property… opens the picker; Remove takes one link away at once, without asking: the
 * models' values stay and come back when the property is added again (§ 5.4).
 * A property on every class (S061 § 5.3) is listed too, marked Every class, with no Remove: it
 * shows on every machine whether linked or not.
 */
import { computed, onMounted, ref } from "vue";
import { apiDelete, apiGet } from "../../api";
import { userPermissions } from "../../stores/auth";
import { ensureProperties, properties } from "../../stores/masters";
import { typeLabel } from "../../utils/propertyFormat";
import AddPropertiesModal from "./AddPropertiesModal.vue";

const props = defineProps({
  // {id, code, name}
  cls: { type: Object, required: true },
});
defineEmits(["back"]);

const canEdit = computed(() => userPermissions.value.includes("equipment:edit"));
const rows = ref(null);
const loadError = ref("");
const actionError = ref("");
const removing = ref(null); // the property id being removed
const picker = ref(null);

const path = computed(() => `/api/masters/equipment-classes/${props.cls.id}/properties`);
const linkedIds = computed(() => (rows.value ?? []).map((r) => r.property_id));

async function load() {
  loadError.value = "";
  try {
    const [answer] = await Promise.all([apiGet(path.value), ensureProperties({ refresh: true })]);
    rows.value = answer.items;
  } catch (err) {
    loadError.value = err.message;
  }
}

async function remove(row) {
  actionError.value = "";
  removing.value = row.property_id;
  try {
    rows.value = (await apiDelete(`${path.value}/${row.property_id}`)).items;
  } catch (err) {
    actionError.value = err.message;
  } finally {
    removing.value = null;
  }
}

function onAdded(answer) {
  rows.value = answer.items;
}

onMounted(load);
</script>

<template>
  <div class="card">
    <div class="card-header d-flex flex-wrap align-items-center gap-1">
      <button class="btn btn-sm btn-link p-0 text-decoration-none" @click="$emit('back')">
        <i class="fa-solid fa-arrow-left me-1"></i>Back
      </button>
      <span>· Properties of {{ cls.code }} — {{ cls.name }}</span>
      <button v-if="canEdit && rows !== null" class="btn btn-sm btn-primary ms-auto" @click="picker.open()">
        <i class="fa-solid fa-plus me-1"></i>Add property…
      </button>
    </div>
    <div class="card-body">
      <p class="form-text mt-0">The data this kind of equipment has. A part's own data, such as its motor's power, goes on the part's class.</p>
      <div v-if="loadError" class="alert alert-danger">{{ loadError }}</div>
      <div v-if="actionError" class="alert alert-danger">{{ actionError }}</div>
      <div v-if="rows === null && !loadError" class="text-secondary">Loading…</div>
      <div v-else-if="rows && rows.length === 0" class="text-secondary">No properties on this class yet.</div>
      <template v-else-if="rows">
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-2">
            <thead>
              <tr><th>Name</th><th>Type</th><th>Unit</th><th v-if="canEdit"></th></tr>
            </thead>
            <tbody>
              <tr v-for="r in rows" :key="r.property_id" :class="{ 'text-secondary': !r.active }">
                <td class="fw-semibold">
                  {{ r.name }}<span v-if="!r.active" class="fw-normal"> (inactive)</span>
                  <span v-if="r.all_classes" class="badge text-bg-info fw-normal ms-1">Every class</span>
                </td>
                <td>{{ typeLabel(r.data_type) }}</td>
                <td>{{ r.unit }}</td>
                <td v-if="canEdit" class="text-end">
                  <button v-if="!r.all_classes" class="btn btn-sm btn-outline-danger" :disabled="removing !== null" @click="remove(r)">Remove</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="small text-secondary">Removing a property keeps the models' values. Add it again to show them.</div>
      </template>
    </div>
  </div>

  <AddPropertiesModal
    v-if="properties"
    ref="picker"
    :cls="cls"
    :properties="properties"
    :linked-ids="linkedIds"
    @saved="onAdded"
  />
</template>
