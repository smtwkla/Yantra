<script setup>
/**
 * The watch's one-line fact (docs/steps/S073-verified-close-screens/1-brief.md § 5.2): whether the
 * symptom came back. Shared by the card *Did it come back?* and the dialog *Verify*, so the
 * verifier decides with the same words in view (D2). Yantra counts, a person decides (ISO 9001
 * § 10.2.1 d): it never says the improvement worked.
 */
import { computed } from "vue";
import { formatDate } from "../../utils/datetime";
import { machinesText, repeatText, symptomsText } from "../../utils/improvementLabels";

const props = defineProps({
  improvement: { type: Object, required: true },
});

const figures = computed(() => props.improvement.watch.figures);
const symptomText = computed(() => symptomsText(figures.value));
const machineText = computed(() => machinesText(figures.value));
const repeats = computed(() => figures.value.repeats);
</script>

<template>
  <div data-testid="watch-summary">
    <p v-if="!figures.symptoms.length" class="mb-2 text-secondary">
      The linked tickets have no symptom yet, so repeats cannot be counted.
    </p>
    <p v-else-if="!repeats.length" class="mb-2 text-success">
      No ticket with the symptom {{ symptomText }} on {{ machineText }} since {{ formatDate(improvement.watch.from) }}.
    </p>
    <div v-else class="alert alert-warning mb-2">
      <i class="fa-solid fa-triangle-exclamation me-1"></i>Came back {{ repeats.length }} {{ repeats.length === 1 ? "time" : "times" }}:
      <template v-for="(r, i) in repeats" :key="r.id">
        <template v-if="i > 0">; </template>
        <router-link :to="`/tickets/${r.id}`" class="alert-link">{{ r.serial }}</router-link> {{ repeatText(r) }}
      </template>.
      Check whether it has the same cause.
    </div>
  </div>
</template>
