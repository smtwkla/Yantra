<script setup>
/**
 * Create / edit dialog for equipment, component-units and components
 * (docs/steps/S003-equipment-screens/1-brief.md § 4.3, § 5.3; type and notes: S004).
 *
 * The parent calls openCreateEquipment(), openCreatePart(parentNode) or openEdit(node)
 * through a template ref and handles @saved ({result, created}). Edit sends only the
 * fields it owns; moving and the status have their own dialogs.
 */
import { computed, ref } from "vue";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ensureMyUnits, myUnits, pickableUnits } from "../../stores/equipment";
import {
  defaultSiteId, ensureEquipmentClasses, ensureEquipmentTypes, ensureSites, ensureUnits, equipmentClasses,
  equipmentTypes, sites, units,
} from "../../stores/masters";
import { LEVEL_LABELS, STATUS_LABELS } from "../../utils/equipmentLabels";

const emit = defineEmits(["saved"]);

const COMMON_BLANK = { class_id: "", type_id: "", name: "", make: "", model: "", serial_no: "", year: "", notes: "" };
// A new record cannot start scrapped; the labels come from the one shared place
const CREATE_STATUSES = Object.entries(STATUS_LABELS).filter(([value]) => value !== "scrapped");

// What the open dialog is about, for display only; nothing here is sent
const NO_CONTEXT = {
  mode: "create-equipment", level: "equipment", parentLevel: null, rootCriticality: null, label: "", place: "",
  currentClassId: null, currentTypeId: null,
};
const context = ref(NO_CONTEXT);
const siteId = ref("");

function blank(seed) {
  if (seed?.parent) {
    return {
      level: seed.parent.level === "equipment" ? "component_unit" : "component",
      parent_id: seed.parent.id,
      ...COMMON_BLANK, criticality: "", status: "in_service",
    };
  }
  return { level: "equipment", unit_id: "", ...COMMON_BLANK, criticality: "C", status: "in_service" };
}

const optionalText = (value) => (String(value ?? "").trim() === "" ? null : String(value).trim());

// Empty optional text is sent as null, the year as a number or null, "inherit" as a null grade, "— none —" as a null type
function toBody(form) {
  const body = { ...form };
  for (const field of ["make", "model", "serial_no", "notes"]) body[field] = optionalText(form[field]);
  body.type_id = form.type_id === "" || form.type_id === null ? null : form.type_id;
  body.year = form.year === "" || form.year === null ? null : Number(form.year);
  body.criticality = form.criticality === "" ? null : form.criticality;
  return body;
}

const {
  modal, form, editingId, saving, dirty, error, fieldError, modalError, openCreate, openEdit: openEditForm, save,
} = useFormModal({
  path: "/api/equipment",
  blank,
  fromRecord: (node) => ({
    class_id: node.class_id,
    type_id: node.type_id ?? "",
    name: node.name,
    make: node.make ?? "",
    model: node.model ?? "",
    serial_no: node.serial_no ?? "",
    year: node.year ?? "",
    criticality: node.criticality ?? "",
    notes: node.notes ?? "",
  }),
  afterSave: (result) => emit("saved", { result, created: editingId.value === null }),
  toBody,
});

const isEdit = computed(() => context.value.mode === "edit");
const isPart = computed(() => context.value.level !== "equipment");

const pickable = computed(() => (myUnits.value ? pickableUnits(units.value, myUnits.value) : []));
const siteChoices = computed(() =>
  (sites.value ?? []).filter((s) => s.active && pickable.value.some((u) => u.site_id === s.id))
);
const unitChoices = computed(() => pickable.value.filter((u) => u.site_id === siteId.value));
// The current class stays listed on edit even if it has since been deactivated
const classChoices = computed(() =>
  (equipmentClasses.value ?? []).filter((c) => c.active || c.id === context.value.currentClassId)
);
// The chosen class's active types; the node's current type stays listed on edit even if since deactivated
const typeChoices = computed(() =>
  (equipmentTypes.value ?? []).filter(
    (t) => t.class_id === form.value.class_id && (t.active || t.id === context.value.currentTypeId)
  )
);
const levelChoices = computed(() =>
  context.value.parentLevel === "equipment" ? ["component_unit", "component"] : ["component"]
);
const inheritLabel = computed(() => `Inherit (${context.value.rootCriticality ?? "?"})`);

const title = computed(() => {
  if (isEdit.value) return `Edit ${context.value.label}`;
  return context.value.mode === "create-part" ? `Add part to ${context.value.label}` : "Add equipment";
});

// A failed load still opens the dialog, with the message at the top
async function open(prepare) {
  let loadError = null;
  try {
    await Promise.all([ensureSites(), ensureUnits(), ensureEquipmentClasses(), ensureEquipmentTypes(), ensureMyUnits()]);
  } catch (err) {
    loadError = err.message;
  }
  prepare();
  if (loadError) error.value = { field: null, message: loadError };
}

function openCreateEquipment() {
  return open(() => {
    context.value = NO_CONTEXT;
    openCreate();
    // One unit: preselect it and its site (this wins over the default site); else the default site
    if (pickable.value.length === 1) {
      siteId.value = pickable.value[0].site_id;
      form.value.unit_id = pickable.value[0].id;
    } else {
      const defaultSite = defaultSiteId();
      siteId.value = siteChoices.value.some((s) => s.id === defaultSite) ? defaultSite : "";
    }
  });
}

function openCreatePart(parent) {
  return open(() => {
    context.value = {
      mode: "create-part",
      level: parent.level === "equipment" ? "component_unit" : "component",
      parentLevel: parent.level,
      rootCriticality: parent.root_criticality,
      label: parent.code,
      place: parent.full_path,
      currentClassId: null,
      currentTypeId: null,
    };
    openCreate({ parent });
  });
}

function openEdit(node) {
  return open(() => {
    context.value = {
      mode: "edit",
      level: node.level,
      parentLevel: null,
      rootCriticality: node.root_criticality,
      label: node.code,
      place: node.level === "equipment" ? node.unit : (node.ancestors.at(-1)?.code ?? ""),
      currentClassId: node.class_id,
      currentTypeId: node.type_id,
    };
    openEditForm(node);
  });
}

defineExpose({ openCreateEquipment, openCreatePart, openEdit });
</script>

<template>
  <FormModal ref="modal" :title="title" :saving="saving" :dirty="dirty" :error="modalError" @save="save">
    <div class="mb-3">
      <label class="form-label" for="eq-level">Level</label>
      <select
        v-if="context.mode === 'create-part'"
        id="eq-level"
        v-model="form.level"
        class="form-select"
        :class="{ 'is-invalid': fieldError('level') }"
      >
        <option v-for="l in levelChoices" :key="l" :value="l">{{ LEVEL_LABELS[l] }}</option>
      </select>
      <div v-else class="form-control-plaintext py-0">{{ LEVEL_LABELS[context.level] }}</div>
      <div v-if="fieldError('level')" class="text-danger small">{{ fieldError("level") }}</div>
    </div>

    <div v-if="context.mode === 'create-equipment'" class="row g-3 mb-3">
      <div class="col-sm-6">
        <label class="form-label" for="eq-site">Site</label>
        <select id="eq-site" v-model="siteId" class="form-select" @change="form.unit_id = ''">
          <option value="" disabled>Select a site…</option>
          <option v-for="s in siteChoices" :key="s.id" :value="s.id">{{ s.code }}</option>
        </select>
      </div>
      <div class="col-sm-6">
        <label class="form-label" for="eq-unit">Unit</label>
        <select id="eq-unit" v-model="form.unit_id" class="form-select" :class="{ 'is-invalid': fieldError('unit_id') }">
          <option value="" disabled>Select a unit…</option>
          <option v-for="u in unitChoices" :key="u.id" :value="u.id">{{ u.code }} — {{ u.name }}</option>
        </select>
        <div class="invalid-feedback">{{ fieldError("unit_id") }}</div>
      </div>
    </div>
    <div v-else class="mb-3">
      <label class="form-label">{{ isPart ? "Parent" : "Unit" }}</label>
      <div class="form-control-plaintext py-0">{{ context.place }}</div>
      <div v-if="fieldError('parent_id')" class="text-danger small">{{ fieldError("parent_id") }}</div>
      <div v-if="isEdit" class="form-text">Changed with Move.</div>
    </div>

    <div class="mb-3">
      <label class="form-label" for="eq-class">Class</label>
      <!-- @change, not a watch: a watch would also fire when fromRecord fills the form and clear the type -->
      <select
        id="eq-class"
        v-model="form.class_id"
        class="form-select"
        :class="{ 'is-invalid': fieldError('class_id') }"
        @change="form.type_id = ''"
      >
        <option value="" disabled>Select a class…</option>
        <option v-for="c in classChoices" :key="c.id" :value="c.id">
          {{ c.code }} — {{ c.name }}{{ c.active ? "" : " (inactive)" }}
        </option>
      </select>
      <div class="invalid-feedback">{{ fieldError("class_id") }}</div>
      <div class="form-text">The class sets the code prefix. Changing it later keeps the code.</div>
    </div>

    <div class="mb-3">
      <label class="form-label" for="eq-type">Type</label>
      <select id="eq-type" v-model="form.type_id" class="form-select" :class="{ 'is-invalid': fieldError('type_id') }">
        <option value="">— none —</option>
        <option v-for="t in typeChoices" :key="t.id" :value="t.id">{{ t.name }}{{ t.active ? "" : " (inactive)" }}</option>
      </select>
      <div class="invalid-feedback">{{ fieldError("type_id") }}</div>
    </div>

    <div class="mb-3">
      <label class="form-label">Code</label>
      <div class="form-control-plaintext py-0">{{ isEdit ? context.label : "Issued on save" }}</div>
    </div>

    <div class="mb-3">
      <label class="form-label" for="eq-name">Name</label>
      <input id="eq-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div class="invalid-feedback">{{ fieldError("name") }}</div>
    </div>

    <div class="row g-3 mb-3">
      <div class="col-sm-4">
        <label class="form-label" for="eq-make">Make</label>
        <input id="eq-make" v-model="form.make" class="form-control" :class="{ 'is-invalid': fieldError('make') }" maxlength="100" />
        <div class="invalid-feedback">{{ fieldError("make") }}</div>
      </div>
      <div class="col-sm-4">
        <label class="form-label" for="eq-model">Model</label>
        <input id="eq-model" v-model="form.model" class="form-control" :class="{ 'is-invalid': fieldError('model') }" maxlength="100" />
        <div class="invalid-feedback">{{ fieldError("model") }}</div>
      </div>
      <div class="col-sm-4">
        <label class="form-label" for="eq-serial">Serial no.</label>
        <input id="eq-serial" v-model="form.serial_no" class="form-control" :class="{ 'is-invalid': fieldError('serial_no') }" maxlength="100" />
        <div class="invalid-feedback">{{ fieldError("serial_no") }}</div>
      </div>
    </div>

    <div class="row g-3">
      <div class="col-sm-4">
        <label class="form-label" for="eq-year">Year</label>
        <input id="eq-year" v-model="form.year" type="number" class="form-control" :class="{ 'is-invalid': fieldError('year') }" />
        <div class="invalid-feedback">{{ fieldError("year") }}</div>
      </div>
      <div class="col-sm-4">
        <label class="form-label" for="eq-crit">Criticality</label>
        <select id="eq-crit" v-model="form.criticality" class="form-select" :class="{ 'is-invalid': fieldError('criticality') }">
          <option v-if="isPart" value="">{{ inheritLabel }}</option>
          <option value="A">A</option>
          <option value="B">B</option>
          <option value="C">C</option>
        </select>
        <div class="invalid-feedback">{{ fieldError("criticality") }}</div>
      </div>
      <div v-if="!isEdit" class="col-sm-4">
        <label class="form-label" for="eq-status">Status</label>
        <select id="eq-status" v-model="form.status" class="form-select" :class="{ 'is-invalid': fieldError('status') }">
          <option v-for="[value, text] in CREATE_STATUSES" :key="value" :value="value">{{ text }}</option>
        </select>
        <div class="invalid-feedback">{{ fieldError("status") }}</div>
      </div>
    </div>

    <div class="mt-3">
      <label class="form-label" for="eq-notes">Notes</label>
      <textarea id="eq-notes" v-model="form.notes" class="form-control" :class="{ 'is-invalid': fieldError('notes') }" rows="4" maxlength="2000"></textarea>
      <div class="invalid-feedback">{{ fieldError("notes") }}</div>
      <div class="form-text">Visible to everyone who can see this equipment — no passwords or prices.</div>
    </div>
  </FormModal>
</template>
