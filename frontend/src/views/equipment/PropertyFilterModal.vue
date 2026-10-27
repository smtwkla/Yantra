<script setup>
/**
 * Filter by property (docs/steps/S062-property-filter/1-brief.md § 5.3): lines of property,
 * operator and value, joined by All conditions or Any condition. It saves nothing, so it uses
 * FormModal directly, not useFormModal: open(filter, classId) copies the filter into the lines,
 * and Apply filter emits `apply` with the new filter (null when no line is left).
 *
 * Apply filter first sends one check request, the list route with per_page=1 (D6), so a value the
 * backend refuses shows under its line and the dialog stays open. The inputs are the dialog's own,
 * not PropertyInput (BR1-05): a line has no label, "between" takes two numbers, and a choice takes
 * several options; they keep PropertyInput's attributes (inputmode, the unit, maxlength).
 */
import { computed, nextTick, ref } from "vue";
import { apiGet } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { ensureProperties, properties } from "../../stores/masters";
import {
  MATCH_ALL, MATCH_ANY, MAX_RULES, encodeFilter, excludesNoValue, filterSnapshot, operatorLabel, operatorsOf, ruleComplete,
  ruleOfLine, takesValue,
} from "../../utils/propertyFilter";

const emit = defineEmits(["apply"]);

const INCOMPLETE = "Complete or remove the empty condition";
const TEXT_MAX = 100; // as PropertyInput and the backend

const modal = ref(null);
const lines = ref([]);
const match = ref(MATCH_ALL);
const classPropertyIds = ref(null); // the ids the list's class shows, or null with no class filter
const saving = ref(false);
const error = ref("");
const lineErrors = ref({}); // {index: {field, message}} from the check request's 400
const initialMatch = ref(MATCH_ALL);
const initialLines = ref([]);
let nextKey = 1;

const byId = computed(() => new Map((properties.value ?? []).map((p) => [p.id, p])));
const dataTypeOf = (line) => byId.value.get(line.property_id)?.data_type;

function emptyLine() {
  return { key: nextKey++, property_id: null, op: "", value: "", low: "", high: "", optionIds: [] };
}

/** A filter rule → a dialog line (the value split by kind). */
function lineOf(rule) {
  const line = { ...emptyLine(), property_id: rule.property_id, op: rule.op ?? "" };
  const value = rule.value;
  if (rule.op === "between" && Array.isArray(value)) {
    [line.low, line.high] = value.map((v) => String(v ?? ""));
  } else if (Array.isArray(value)) {
    line.optionIds = [...value];
  } else if (typeof value === "boolean") {
    line.value = String(value);
  } else if (value !== undefined && value !== null) {
    line.value = String(value);
  }
  return line;
}

const ruleOf = (line) => ruleOfLine(line, dataTypeOf(line));

// The starting state is kept as a copy and compared with the same data types each time, because
// the property list may load after the dialog opens (CR2-01)
const dirty = computed(
  () => filterSnapshot(initialMatch.value, initialLines.value, dataTypeOf) !== filterSnapshot(match.value, lines.value, dataTypeOf)
);

const incomplete = computed(() => lines.value.some((line) => !ruleComplete(ruleOf(line), dataTypeOf(line))));
const disabledReason = computed(() => (incomplete.value ? INCOMPLETE : ""));

// The active properties by name; with a class filter, only those the class shows (BS1-05)
const choices = computed(() =>
  (properties.value ?? [])
    .filter((p) => p.active && (classPropertyIds.value === null || classPropertyIds.value.has(p.id)))
    .sort((a, b) => a.name.localeCompare(b.name))
);

/** The property select's list for a line: its own property last when the list lacks it (a bookmark). */
function lineChoices(line) {
  if (line.property_id === null || choices.value.some((p) => p.id === line.property_id)) return choices.value;
  const own = byId.value.get(line.property_id);
  return [...choices.value, own ?? { id: line.property_id, name: `#${line.property_id}`, active: true }];
}

function propertyText(p) {
  const name = p.unit ? `${p.name} (${p.unit})` : p.name;
  return p.active ? name : `${name} (inactive)`;
}

// A choice's options: the active ones first, an inactive one marked
function optionsOf(line) {
  const options = byId.value.get(line.property_id)?.options ?? [];
  return [...options].sort((a, b) => Number(b.active) - Number(a.active));
}

function chooseProperty(line) {
  line.op = operatorsOf(dataTypeOf(line))[0] ?? "";
  line.value = "";
  line.low = "";
  line.high = "";
  line.optionIds = [];
}

function addLine() {
  if (lines.value.length < MAX_RULES) lines.value.push(emptyLine());
}

function removeLine(index) {
  lines.value.splice(index, 1);
  lineErrors.value = {};
}

const errorOf = (index, field) => (lineErrors.value[index]?.field === field ? lineErrors.value[index].message : "");

async function loadChoices(classId) {
  await ensureProperties();
  if (!classId) {
    classPropertyIds.value = null;
    return;
  }
  const { items } = await apiGet(`/api/masters/equipment-classes/${classId}/properties`);
  classPropertyIds.value = new Set(items.map((item) => item.property_id));
}

/** filter: the decoded filter, or null (no filter, or one that cannot be read): one empty line. */
async function open(filter, classId) {
  error.value = "";
  lineErrors.value = {};
  saving.value = false;
  match.value = filter?.match === MATCH_ANY ? MATCH_ANY : MATCH_ALL;
  lines.value = filter?.rules?.length ? filter.rules.map(lineOf) : [emptyLine()];
  initialMatch.value = match.value;
  initialLines.value = JSON.parse(JSON.stringify(lines.value));
  modal.value.open(); // shown at once; the property list fills in when its reads finish
  try {
    await loadChoices(classId);
  } catch (err) {
    error.value = err.message;
  }
}

const LINE_FIELD = /^props\.rules\.(\d+)(?:\.(property_id|op|value))?$/;

async function apply() {
  error.value = "";
  lineErrors.value = {};
  const filter = lines.value.length ? { match: match.value, rules: lines.value.map(ruleOf) } : null;
  if (filter) {
    saving.value = true;
    try {
      const params = new URLSearchParams({ props: encodeFilter(filter), level: "all", per_page: "1" });
      await apiGet(`/api/equipment?${params}`);
    } catch (err) {
      const found = err.status === 400 ? LINE_FIELD.exec(err.field ?? "") : null;
      if (found) {
        lineErrors.value = { [found[1]]: { field: found[2] ?? "property_id", message: err.message } };
        await nextTick();
        modal.value.revealError();
      } else {
        error.value = err.message;
      }
      return;
    } finally {
      saving.value = false;
    }
  }
  emit("apply", filter);
  modal.value.close();
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    title="Filter by property"
    save-label="Apply filter"
    :saving="saving"
    :error="error"
    :dirty="dirty"
    :save-disabled-reason="disabledReason"
    @save="apply"
  >
    <fieldset v-if="lines.length >= 2" class="mb-3">
      <legend class="form-label fs-6 mb-1">Match</legend>
      <div class="form-check form-check-inline">
        <input id="pf-match-all" v-model="match" class="form-check-input" type="radio" :value="MATCH_ALL" />
        <label class="form-check-label" for="pf-match-all">All conditions</label>
      </div>
      <div class="form-check form-check-inline">
        <input id="pf-match-any" v-model="match" class="form-check-input" type="radio" :value="MATCH_ANY" />
        <label class="form-check-label" for="pf-match-any">Any condition</label>
      </div>
    </fieldset>

    <div v-for="(line, index) in lines" :key="line.key" class="filter-line border rounded p-2 mb-2" data-test="condition">
      <div class="d-flex gap-2 align-items-start">
        <div class="flex-grow-1 min-w-0">
          <select
            v-model="line.property_id"
            class="form-select"
            :class="{ 'is-invalid': errorOf(index, 'property_id') }"
            :aria-label="`Property ${index + 1}`"
            @change="chooseProperty(line)"
          >
            <option :value="null" disabled>Choose a property</option>
            <option v-for="p in lineChoices(line)" :key="p.id" :value="p.id">{{ propertyText(p) }}</option>
          </select>
          <div v-if="errorOf(index, 'property_id')" class="invalid-feedback d-block">{{ errorOf(index, "property_id") }}</div>
        </div>
        <button
          type="button"
          class="btn btn-outline-danger"
          title="Remove condition"
          aria-label="Remove condition"
          @click="removeLine(index)"
        >
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>

      <div v-if="line.property_id !== null" class="d-flex flex-wrap gap-2 mt-2 align-items-start">
        <div>
          <select
            v-model="line.op"
            class="form-select w-auto"
            :class="{ 'is-invalid': errorOf(index, 'op') }"
            :aria-label="`Operator ${index + 1}`"
          >
            <option v-for="op in operatorsOf(dataTypeOf(line))" :key="op" :value="op">{{ operatorLabel(dataTypeOf(line), op) }}</option>
          </select>
          <div v-if="errorOf(index, 'op')" class="invalid-feedback d-block">{{ errorOf(index, "op") }}</div>
        </div>

        <div v-if="takesValue(line.op)" class="value-cell flex-grow-1">
          <div v-if="line.op === 'between'" class="d-flex align-items-center gap-2">
            <div class="input-group">
              <input
                v-model="line.low"
                class="form-control"
                :class="{ 'is-invalid': errorOf(index, 'value') }"
                type="text"
                inputmode="decimal"
                autocomplete="off"
                :aria-label="`Value ${index + 1}`"
              />
            </div>
            <span>and</span>
            <div class="input-group">
              <input
                v-model="line.high"
                class="form-control"
                :class="{ 'is-invalid': errorOf(index, 'value') }"
                type="text"
                inputmode="decimal"
                autocomplete="off"
                :aria-label="`Second value ${index + 1}`"
              />
              <span v-if="byId.get(line.property_id)?.unit" class="input-group-text">{{ byId.get(line.property_id).unit }}</span>
            </div>
          </div>
          <div v-else-if="dataTypeOf(line) === 'number'" class="input-group">
            <input
              v-model="line.value"
              class="form-control"
              :class="{ 'is-invalid': errorOf(index, 'value') }"
              type="text"
              inputmode="decimal"
              autocomplete="off"
              :aria-label="`Value ${index + 1}`"
            />
            <span v-if="byId.get(line.property_id)?.unit" class="input-group-text">{{ byId.get(line.property_id).unit }}</span>
          </div>
          <div v-else-if="dataTypeOf(line) === 'choice'" role="group" :aria-label="`Value ${index + 1}`">
            <div v-for="o in optionsOf(line)" :key="o.id" class="form-check">
              <input
                :id="`pf-${line.key}-option-${o.id}`"
                v-model="line.optionIds"
                class="form-check-input"
                :class="{ 'is-invalid': errorOf(index, 'value') }"
                type="checkbox"
                :value="o.id"
              />
              <label class="form-check-label" :for="`pf-${line.key}-option-${o.id}`">{{ o.label }}{{ o.active ? "" : " (inactive)" }}</label>
            </div>
          </div>
          <input
            v-else-if="dataTypeOf(line) === 'text'"
            v-model="line.value"
            class="form-control"
            :class="{ 'is-invalid': errorOf(index, 'value') }"
            :maxlength="TEXT_MAX"
            :aria-label="`Value ${index + 1}`"
          />
          <select
            v-else-if="dataTypeOf(line) === 'yes_no'"
            v-model="line.value"
            class="form-select w-auto"
            :class="{ 'is-invalid': errorOf(index, 'value') }"
            :aria-label="`Value ${index + 1}`"
          >
            <option value="" disabled>Choose Yes or No</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
          <div v-if="errorOf(index, 'value')" class="invalid-feedback d-block">{{ errorOf(index, "value") }}</div>
        </div>
      </div>
      <div v-if="excludesNoValue(line.op)" class="form-text">Machines with no value are not included.</div>
    </div>

    <button v-if="lines.length < MAX_RULES" type="button" class="btn btn-sm btn-outline-primary" @click="addLine">
      <i class="fa-solid fa-plus me-1"></i>Add condition
    </button>
    <div v-else class="form-text">{{ MAX_RULES }} conditions at most</div>
    <!-- The disabled Apply filter's reason shows in FormModal's footer on every width (S064 UX-05) -->
  </FormModal>
</template>

<style scoped>
.min-w-0 {
  min-width: 0;
}

.value-cell {
  min-width: 8rem;
}
</style>
