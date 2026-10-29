<script setup>
/**
 * The dialog *Verify* (docs/steps/S073-verified-close-screens/1-brief.md § 5.3): one dialog for
 * both decisions. `open("effective")` closes the improvement as it worked; `open("not_effective")`
 * closes it as it did not work and starts the follow-up, and the router goes there (D7). The mode
 * is a ref, not a form field: it picks the route, the title, the label and the need for a remark.
 * ISO 9001 § 10.2.1 d: the verifier sees the facts above the remark and writes why.
 */
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { apiPost } from "../../api";
import FormModal from "../../components/FormModal.vue";
import { useFormModal } from "../../composables/useFormModal";
import { CLOSE_REMARK_MAX } from "../../utils/improvementLabels";
import WatchSummary from "./WatchSummary.vue";

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["saved", "reload"]);

const router = useRouter();
const mode = ref("effective");
const worked = computed(() => mode.value === "effective");

const { modal, form, saving, dirty, error, fieldError, modalError, openCreate, send } = useFormModal({
  path: null,
  blank: () => ({ remark: "" }),
  afterSave: (result) => {
    if (worked.value) emit("saved", result);
    else router.push(`/tickets/improvements/${result.id}`);
  },
});

// A stale page (409, no field): the improvement was closed or changed meanwhile
watch(error, (value) => {
  if (value && !value.field && value.status === 409) emit("reload");
});

function open(newMode) {
  mode.value = newMode;
  openCreate();
}

function save() {
  const route = worked.value ? "effective" : "not-effective";
  return send(() => apiPost(`/api/improvements/${props.improvement.id}/verify/${route}`, { remark: form.value.remark }));
}

defineExpose({ open });
</script>

<template>
  <FormModal
    ref="modal"
    :title="worked ? 'Close: it worked' : 'Did not work — analyse again'"
    :save-label="worked ? 'Close: it worked' : 'Close and analyse again'"
    :saving="saving"
    :dirty="dirty"
    :error="modalError"
    @save="save"
  >
    <WatchSummary v-if="improvement.watch.figures" :improvement="improvement" />
    <p class="fw-semibold" data-testid="verify-consequence">
      <template v-if="worked">{{ improvement.serial }} closes and cannot be changed after.</template>
      <template v-else>
        {{ improvement.serial }} closes: it did not work. A new improvement starts with its tickets, and you go there.
      </template>
    </p>
    <div class="mb-3">
      <label class="form-label" for="verify-remark">{{ worked ? "Remark (optional)" : "Why did it not work?" }}</label>
      <textarea
        id="verify-remark"
        v-model="form.remark"
        class="form-control"
        :class="{ 'is-invalid': fieldError('remark') }"
        rows="3"
        :maxlength="CLOSE_REMARK_MAX"
        :aria-describedby="worked ? 'verify-remark-help' : null"
      ></textarea>
      <div v-if="fieldError('remark')" class="invalid-feedback d-block">{{ fieldError("remark") }}</div>
      <div v-if="worked" id="verify-remark-help" class="form-text">
        What you checked, for example the panels on three presses. This records the fix as effective (ISO 9001 § 10.2).
      </div>
    </div>
  </FormModal>
</template>
