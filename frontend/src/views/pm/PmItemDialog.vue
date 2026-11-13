<script setup>
/**
 * Add item / Edit item of a PM template (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.10, mock-up 14;
 * S096 before it): the type (Task, Check, Reading), what to do or check, for a reading its kind — a *Measurement*
 * (its own unit and limits; the value stays on the job) or a *Meter reading* (a counter or gauge meter type; the
 * value is saved as a reading of each machine's meter of that type, its own or a linked one (S104 A1), with that
 * meter's unit and limits) — help text and the photo setting.
 *
 * Call contract (repo self-check (13)): `openAdd()` opens a blank Check with an optional photo (blank() takes no
 * seed); `openEditAt(item, index)` opens the page's item number index + 1. The dialog writes nothing: Save item asks
 * `POST /api/pm/template-item-check`, the template save's own rules (S096 D2), so a refusal shows beside its field at
 * once. Its answer is the clean item; `done({ item, index })` hands it to the page, which puts it into its list (a
 * new one at the end, index null). "Remove item" asks in place, then emits `remove(index)`; the item goes when the
 * template is saved.
 */
import { computed, ref } from "vue";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import {
  blankItemForm, ITEM_TYPES, itemBody, itemForm, itemType, PHOTO_SETTINGS, READING_KINDS,
} from "../../utils/pmLabels";

const props = defineProps({
  meterTypes: { type: Array, default: () => [] }, // the counter and gauge meter types (Masters › Meter types)
});
const emit = defineEmits(["done", "remove"]);

const PATH = "/api/pm/template-item-check";
// The fields a refusal can name in this dialog; any other shows at the top
const FIELDS = ["item_type", "text", "help_text", "photo", "reading_kind", "unit", "meter_type_id", "min_value",
  "max_value"];

const editIndex = ref(null); // the page's index of the item being edited; null when adding
const confirmingRemove = ref(false);

const { modal, form, saving, dirty, error, fieldError, openCreate, openEdit, send } = useFormModal({
  path: PATH,
  blank: blankItemForm,
  fromRecord: itemForm,
  toBody: itemBody,
  label: (item) => item.text,
  afterSave: (item) => emit("done", { item, index: editIndex.value }),
});

const topError = computed(() => (error.value && !FIELDS.includes(error.value.field) ? error.value.message : ""));
const isReading = computed(() => form.value.item_type === "reading");
const isMeasurement = computed(() => isReading.value && form.value.reading_kind === "measurement");
const isMeterReading = computed(() => isReading.value && form.value.reading_kind === "meter");
// The active counters and gauges, and the item's own type when it is no longer one of them
const meterChoices = computed(() => props.meterTypes.filter(
  (t) => ["counter", "gauge"].includes(t.kind) && (t.active || t.id === Number(form.value.meter_type_id))));

const TEXT_HELP = {
  task: "For example: Grease the main bearing",
  check: "For example: No oil leaks at the cylinder seals",
  reading: "For example: Main pressure at full load",
};

function openAdd() {
  editIndex.value = null;
  confirmingRemove.value = false;
  openCreate();
}

function openEditAt(item, index) {
  editIndex.value = index;
  confirmingRemove.value = false;
  openEdit(item);
}

function save() {
  return send(() => apiPost(PATH, { item: itemBody(form.value) }));
}

function remove() {
  emit("remove", editIndex.value);
  modal.value.close();
}

defineExpose({ openAdd, openEditAt });
</script>

<template>
  <FormModal
    ref="modal"
    :title="editIndex === null ? 'Add item' : `Edit item ${editIndex + 1}`"
    :saving="saving"
    :dirty="dirty"
    :error="topError"
    save-label="Save item"
    @save="save"
  >
    <template v-if="editIndex !== null" #footer-left>
      <span v-if="confirmingRemove" class="d-inline-flex flex-wrap align-items-center gap-2">
        <span>Remove item {{ editIndex + 1 }}? It goes when you save the template.</span>
        <button type="button" class="btn btn-sm btn-danger tap-target" @click="remove">Yes</button>
        <button type="button" class="btn btn-sm btn-outline-secondary tap-target" @click="confirmingRemove = false">No</button>
      </span>
      <button v-else type="button" class="btn btn-outline-danger" :disabled="saving" @click="confirmingRemove = true">
        Remove item
      </button>
    </template>

    <div class="mb-3">
      <div class="btn-group w-100" role="group" aria-label="Type">
        <template v-for="t in ITEM_TYPES" :key="t.value">
          <input :id="`pm-item-type-${t.value}`" v-model="form.item_type" type="radio" class="btn-check" :value="t.value" />
          <label class="btn btn-outline-primary tap-target" :for="`pm-item-type-${t.value}`">{{ t.label }}</label>
        </template>
      </div>
      <div class="form-text">{{ itemType(form.item_type).legend }}</div>
      <div v-if="fieldError('item_type')" class="invalid-feedback d-block">{{ fieldError("item_type") }}</div>
    </div>

    <div class="mb-3">
      <label class="form-label" for="pm-item-text">What to do or check</label>
      <input
        id="pm-item-text"
        v-model="form.text"
        class="form-control"
        :class="{ 'is-invalid': fieldError('text') }"
        maxlength="200"
        autocomplete="off"
        autofocus
      />
      <div class="form-text">{{ TEXT_HELP[form.item_type] }}</div>
      <div v-if="fieldError('text')" class="invalid-feedback d-block">{{ fieldError("text") }}</div>
    </div>

    <template v-if="isReading">
      <fieldset class="mb-3" data-testid="pm-reading-kind">
        <legend class="form-label fs-6 mb-1">What kind of reading?</legend>
        <div v-for="k in READING_KINDS" :key="k.value" class="form-check">
          <input :id="`pm-reading-${k.value}`" v-model="form.reading_kind" class="form-check-input" type="radio" :value="k.value" />
          <label class="form-check-label" :for="`pm-reading-${k.value}`">{{ k.label }}</label>
          <div class="form-text mt-0">{{ k.help }}</div>
        </div>
        <div v-if="fieldError('reading_kind')" class="invalid-feedback d-block">{{ fieldError("reading_kind") }}</div>
      </fieldset>

      <template v-if="isMeasurement">
        <div class="mb-3">
          <label class="form-label" for="pm-item-unit">Unit</label>
          <input id="pm-item-unit" v-model="form.unit" class="form-control" :class="{ 'is-invalid': fieldError('unit') }" maxlength="20" autocomplete="off" />
          <div class="form-text">For example: bar, mm, °C</div>
          <div v-if="fieldError('unit')" class="invalid-feedback d-block">{{ fieldError("unit") }}</div>
        </div>
        <div class="row g-3 mb-3">
          <div class="col-6">
            <label class="form-label" for="pm-item-min">Min</label>
            <div class="input-group">
              <input id="pm-item-min" v-model="form.min_value" class="form-control" :class="{ 'is-invalid': fieldError('min_value') }" inputmode="decimal" autocomplete="off" />
              <span v-if="form.unit" class="input-group-text">{{ form.unit }}</span>
            </div>
            <div v-if="fieldError('min_value')" class="invalid-feedback d-block">{{ fieldError("min_value") }}</div>
          </div>
          <div class="col-6">
            <label class="form-label" for="pm-item-max">Max</label>
            <div class="input-group">
              <input id="pm-item-max" v-model="form.max_value" class="form-control" :class="{ 'is-invalid': fieldError('max_value') }" inputmode="decimal" autocomplete="off" />
              <span v-if="form.unit" class="input-group-text">{{ form.unit }}</span>
            </div>
            <div v-if="fieldError('max_value')" class="invalid-feedback d-block">{{ fieldError("max_value") }}</div>
          </div>
          <div class="col-12 form-text mt-1">Out of these limits, the job marks the value High or Low.</div>
        </div>
      </template>

      <template v-if="isMeterReading">
        <div class="mb-3">
          <label class="form-label" for="pm-item-meter-type">Meter type</label>
          <select id="pm-item-meter-type" v-model="form.meter_type_id" class="form-select" :class="{ 'is-invalid': fieldError('meter_type_id') }">
            <option value="">Choose a meter type…</option>
            <option v-for="t in meterChoices" :key="t.id" :value="t.id">{{ t.unit ? `${t.name} (${t.unit})` : t.name }}</option>
          </select>
          <div class="form-text">Unit and limits come from each machine's meter.</div>
          <div v-if="fieldError('meter_type_id')" class="invalid-feedback d-block">{{ fieldError("meter_type_id") }}</div>
        </div>
      </template>
    </template>

    <div class="mb-3">
      <label class="form-label" for="pm-item-help">Help text</label>
      <textarea id="pm-item-help" v-model="form.help_text" class="form-control" :class="{ 'is-invalid': fieldError('help_text') }" rows="2" maxlength="500"></textarea>
      <div class="form-text">How to do it, or what good looks like.</div>
      <div v-if="fieldError('help_text')" class="invalid-feedback d-block">{{ fieldError("help_text") }}</div>
    </div>

    <div class="mb-1">
      <label class="form-label" for="pm-item-photo">Photo</label>
      <select id="pm-item-photo" v-model="form.photo" class="form-select" :class="{ 'is-invalid': fieldError('photo') }">
        <option v-for="p in PHOTO_SETTINGS" :key="p.value" :value="p.value">{{ p.label }}</option>
      </select>
      <div v-if="fieldError('photo')" class="invalid-feedback d-block">{{ fieldError("photo") }}</div>
    </div>
  </FormModal>
</template>
