<script setup>
/**
 * Create / edit dialog for equipment, component-units and components
 * (docs/steps/S003-equipment-screens/1-brief.md § 4.3, § 5.3; notes: S004; model: S012).
 *
 * The parent calls openCreateEquipment(), openCreatePart(parentNode) or openEdit(node)
 * through a template ref and handles @saved ({result, created}). Edit sends only the
 * fields it owns; moving and the lifecycle have their own dialogs.
 *
 * The node picks its model (S012 § 1.4); its class and type come from the model and are shown,
 * not picked. The class filter only narrows the model list and is not sent.
 *
 * A component-unit may pick *No model* (S033 § 1.5): the Class (required) and Type (optional)
 * selects then show instead of the class filter. class_id and type_id are form keys in every
 * state, so a refusal on them shows beside the field; toBody sends them only with No model.
 * "" in a select is "nothing picked": the Model placeholder, the Class placeholder, "No type".
 */
import { computed, ref } from "vue";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { ensureMyUnits, myUnits, pickableUnits } from "../../stores/equipment";
import {
  defaultSiteId, ensureEquipmentClasses, ensureEquipmentTypes, ensureModels, ensureSites, ensureUnits,
  equipmentClasses, equipmentModels, equipmentTypes, sites, units,
} from "../../stores/masters";
import { LEVEL_LABELS, LIFECYCLE_LABELS } from "../../utils/equipmentLabels";
import {
  NO_MODEL, NO_MODEL_LEVEL, classHasNoModel, modelChoices, noModelClassChoices, noModelDefaults, noModelTypeChoices,
} from "../../utils/modelPicker";

const emit = defineEmits(["saved"]);

const COMMON_BLANK = { model_id: "", class_id: "", type_id: "", name: "", serial_no: "", year: "", notes: "" };
// A new record cannot start scrapped; the labels come from the one shared place
const CREATE_LIFECYCLES = Object.entries(LIFECYCLE_LABELS).filter(([value]) => value !== "scrapped");

// What the open dialog is about, for display only; nothing here is sent
const NO_CONTEXT = {
  mode: "create-equipment", level: "equipment", parentLevel: null, rootCriticality: null, label: "", place: "",
  currentModelId: null, currentClassId: null, currentTypeId: null,
};
const context = ref(NO_CONTEXT);
const siteId = ref("");
const classFilter = ref("");

function blank(seed) {
  if (seed?.parent) {
    return {
      level: seed.parent.level === "equipment" ? "component_unit" : "component",
      parent_id: seed.parent.id,
      ...COMMON_BLANK, criticality: "", lifecycle: "in_service",
    };
  }
  return { level: "equipment", unit_id: "", ...COMMON_BLANK, criticality: "C", lifecycle: "in_service" };
}

const optionalText = (value) => (String(value ?? "").trim() === "" ? null : String(value).trim());

const nullIfEmpty = (value) => (value === "" ? null : value);

// Empty optional text is sent as null, the year as a number or null, "inherit" as a null grade.
// The model (S033 § 1.5): nothing picked leaves model_id, class_id and type_id out, which the
// backend refuses with "Pick a model"; No model sends model_id null with the class (null for the
// placeholder: "Pick a class") and the type (null for No type); a model sends model_id only.
function toBody(form) {
  const { class_id: classId, type_id: typeId, ...body } = form;
  for (const field of ["serial_no", "notes"]) body[field] = optionalText(form[field]);
  if (form.model_id === "") {
    delete body.model_id;
  } else if (form.model_id === NO_MODEL) {
    Object.assign(body, { model_id: null, class_id: nullIfEmpty(classId), type_id: nullIfEmpty(typeId) });
  }
  body.year = form.year === "" || form.year === null ? null : Number(form.year);
  body.criticality = nullIfEmpty(form.criticality);
  return body;
}

const {
  modal, form, editingId, saving, dirty, error, fieldError, modalError, openCreate, openEdit: openEditForm, save,
} = useFormModal({
  path: "/api/equipment",
  blank,
  fromRecord: (node) => ({
    model_id: node.model_id ?? NO_MODEL,
    class_id: node.class_id,
    type_id: node.type_id ?? "",
    name: node.name,
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
// The class filter offers active classes only: it narrows the models that may be newly picked
const classChoices = computed(() => (equipmentClasses.value ?? []).filter((c) => c.active));
// The level being created or edited: the Add part dialog's select, else the node's
const level = computed(() => form.value.level ?? context.value.level);
const noModel = computed(() => form.value.model_id === NO_MODEL);
const modelOptions = computed(() =>
  modelChoices(equipmentModels.value, {
    classId: classFilter.value,
    currentId: context.value.currentModelId,
    selectedId: form.value.model_id,
    level: level.value,
  })
);
const noModelClasses = computed(() => noModelClassChoices(equipmentClasses.value, context.value.currentClassId));
const noModelTypes = computed(() =>
  noModelTypeChoices(equipmentTypes.value, form.value.class_id, context.value.currentTypeId)
);
const pickedModel = computed(() => (equipmentModels.value ?? []).find((m) => m.id === form.value.model_id) ?? null);
const showNoModelHint = computed(() => !noModel.value && classHasNoModel(equipmentModels.value, classFilter.value));

// Picking No model prefills the class from the class filter, else the node's own (on edit), and
// the type from the node when the class is the node's (S033 § 1.5)
function onModelChange() {
  if (!noModel.value) return;
  const { currentClassId, currentTypeId } = context.value;
  Object.assign(form.value, noModelDefaults({ classFilter: classFilter.value, currentClassId, currentTypeId }));
}

// A type belongs to one class: a new class starts at No type
function onClassChange() {
  form.value.type_id = "";
}

// Only a component-unit may have no model
function onLevelChange() {
  if (noModel.value && form.value.level !== NO_MODEL_LEVEL) form.value.model_id = "";
}
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
    await Promise.all([
      ensureSites(), ensureUnits(), ensureEquipmentClasses(), ensureEquipmentTypes(), ensureModels(), ensureMyUnits(),
    ]);
  } catch (err) {
    loadError = err.message;
  }
  classFilter.value = "";
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
      currentModelId: null,
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
      currentModelId: node.model_id,
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
        @change="onLevelChange"
      >
        <option v-for="l in levelChoices" :key="l" :value="l">{{ LEVEL_LABELS[l] }}</option>
      </select>
      <div v-else class="form-control-plaintext py-0">{{ LEVEL_LABELS[context.level] }}</div>
      <div v-if="fieldError('level')" class="invalid-feedback d-block">{{ fieldError("level") }}</div>
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
        <div v-if="fieldError('unit_id')" class="invalid-feedback d-block">{{ fieldError("unit_id") }}</div>
      </div>
    </div>
    <div v-else class="mb-3">
      <label class="form-label">{{ isPart ? "Parent" : "Unit" }}</label>
      <div class="form-control-plaintext py-0">{{ context.place }}</div>
      <div v-if="fieldError('parent_id')" class="invalid-feedback d-block">{{ fieldError("parent_id") }}</div>
      <div v-if="isEdit" class="form-text">Changed with Move.</div>
    </div>

    <div v-if="!noModel" class="mb-2">
      <label class="form-label" for="eq-class-filter">Class filter</label>
      <select id="eq-class-filter" v-model="classFilter" class="form-select form-select-sm">
        <option value="">All classes</option>
        <option v-for="c in classChoices" :key="c.id" :value="c.id">{{ c.code }} — {{ c.name }}</option>
      </select>
    </div>

    <div class="mb-3">
      <label class="form-label" for="eq-model">Model</label>
      <select
        id="eq-model"
        v-model="form.model_id"
        class="form-select"
        :class="{ 'is-invalid': fieldError('model_id') }"
        @change="onModelChange"
      >
        <option value="" disabled>Select a model…</option>
        <option v-for="m in modelOptions" :key="m.id" :value="m.id">{{ m.text }}</option>
      </select>
      <div v-if="fieldError('model_id')" class="invalid-feedback d-block">{{ fieldError("model_id") }}</div>
      <div v-if="showNoModelHint" class="form-text">
        <template v-if="level === NO_MODEL_LEVEL">
          This class has no model yet. Pick No model, or add a model in Masters › Models.
        </template>
        <template v-else>
          This class has no model yet. Add a model in Masters › Models (a Generic one if the maker is unknown).
        </template>
      </div>
      <div v-if="pickedModel" class="form-text">
        Class: {{ pickedModel.class_code }} — {{ pickedModel.class_name }} · Type: {{ pickedModel.type_name ?? "none" }}
      </div>
      <div v-if="noModel" class="form-text">Without a model, the class sets the code prefix. A later class change keeps the code.</div>
      <div v-else class="form-text">The model's class sets the code prefix. A model of another class later keeps the code.</div>
    </div>

    <div v-if="noModel" class="row g-3 mb-3">
      <div class="col-sm-6">
        <label class="form-label" for="eq-class">Class</label>
        <select
          id="eq-class"
          v-model="form.class_id"
          class="form-select"
          :class="{ 'is-invalid': fieldError('class_id') }"
          @change="onClassChange"
        >
          <option value="" disabled>Select a class…</option>
          <option v-for="c in noModelClasses" :key="c.id" :value="c.id">{{ c.text }}</option>
        </select>
        <div v-if="fieldError('class_id')" class="invalid-feedback d-block">{{ fieldError("class_id") }}</div>
      </div>
      <div class="col-sm-6">
        <label class="form-label" for="eq-type">Type</label>
        <select id="eq-type" v-model="form.type_id" class="form-select" :class="{ 'is-invalid': fieldError('type_id') }">
          <option value="">No type</option>
          <option v-for="t in noModelTypes" :key="t.id" :value="t.id">{{ t.text }}</option>
        </select>
        <div v-if="fieldError('type_id')" class="invalid-feedback d-block">{{ fieldError("type_id") }}</div>
      </div>
    </div>

    <div class="mb-3">
      <label class="form-label">Code</label>
      <div class="form-control-plaintext py-0">{{ isEdit ? context.label : "Issued on save" }}</div>
    </div>

    <div class="mb-3">
      <label class="form-label" for="eq-name">Name</label>
      <input id="eq-name" v-model="form.name" class="form-control" :class="{ 'is-invalid': fieldError('name') }" maxlength="100" />
      <div v-if="fieldError('name')" class="invalid-feedback d-block">{{ fieldError("name") }}</div>
    </div>

    <div class="row g-3">
      <div class="col-sm-4">
        <label class="form-label" for="eq-serial">Serial no.</label>
        <input id="eq-serial" v-model="form.serial_no" class="form-control" :class="{ 'is-invalid': fieldError('serial_no') }" maxlength="100" />
        <div v-if="fieldError('serial_no')" class="invalid-feedback d-block">{{ fieldError("serial_no") }}</div>
      </div>
      <div class="col-sm-4">
        <label class="form-label" for="eq-year">Year</label>
        <input id="eq-year" v-model="form.year" type="number" class="form-control" :class="{ 'is-invalid': fieldError('year') }" />
        <div v-if="fieldError('year')" class="invalid-feedback d-block">{{ fieldError("year") }}</div>
      </div>
      <div class="col-sm-4">
        <label class="form-label" for="eq-crit">Criticality</label>
        <select id="eq-crit" v-model="form.criticality" class="form-select" :class="{ 'is-invalid': fieldError('criticality') }">
          <option v-if="isPart" value="">{{ inheritLabel }}</option>
          <option value="A">A</option>
          <option value="B">B</option>
          <option value="C">C</option>
        </select>
        <div v-if="fieldError('criticality')" class="invalid-feedback d-block">{{ fieldError("criticality") }}</div>
      </div>
      <div v-if="!isEdit" class="col-sm-4">
        <label class="form-label" for="eq-lifecycle">Lifecycle</label>
        <select id="eq-lifecycle" v-model="form.lifecycle" class="form-select" :class="{ 'is-invalid': fieldError('lifecycle') }">
          <option v-for="[value, text] in CREATE_LIFECYCLES" :key="value" :value="value">{{ text }}</option>
        </select>
        <div v-if="fieldError('lifecycle')" class="invalid-feedback d-block">{{ fieldError("lifecycle") }}</div>
      </div>
      <div class="col-12 form-text mt-1">
        Criticality —
        <strong>A</strong>: stops a production line, or is a safety or environment risk; no standby.
        <strong>B</strong>: slows production, or has a standby; repair within the shift.
        <strong>C</strong>: no direct effect on production; repair when convenient.
        <template v-if="isPart">A component-unit or component without its own grade takes its equipment's grade.</template>
      </div>
    </div>

    <div class="mt-3">
      <label class="form-label" for="eq-notes">Notes</label>
      <textarea id="eq-notes" v-model="form.notes" class="form-control" :class="{ 'is-invalid': fieldError('notes') }" rows="4" maxlength="2000"></textarea>
      <div v-if="fieldError('notes')" class="invalid-feedback d-block">{{ fieldError("notes") }}</div>
      <div class="form-text">Visible to everyone who can see this equipment — no passwords or prices.</div>
    </div>
  </FormModal>
</template>
