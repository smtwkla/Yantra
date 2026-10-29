<script setup>
/**
 * The card *Did it come back?* (docs/steps/S073-verified-close-screens/1-brief.md § 5.2; mock-up
 * docs/roadmap/R05-mockups/05-verify.html). Shown by the page once the watch has started. The
 * watch's facts are S072's `watch.figures`; the card computes nothing of its own. The two
 * decisions open the Verify dialog, which the page owns: `verify("effective" | "not_effective")`.
 */
import { computed } from "vue";
import { figureRows, machinesText } from "../../utils/improvementLabels";
import WatchSummary from "./WatchSummary.vue";

const props = defineProps({
  improvement: { type: Object, required: true },
});
const emit = defineEmits(["verify", "edit-watch"]);

const table = computed(() => figureRows(props.improvement.watch.figures, props.improvement.closed, props.improvement.watch.ended));
const machineText = computed(() => machinesText(props.improvement.watch.figures));
const waitingForDecision = computed(() => props.improvement.state === "ready_to_verify" && !props.improvement.can_verify);
</script>

<template>
  <div class="card mt-3" data-testid="watch-card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span>Did it come back?</span>
      <button v-if="improvement.can_edit_watch" type="button" class="btn btn-outline-primary" @click="emit('edit-watch')">
        Change watch
      </button>
    </div>
    <div class="card-body">
      <WatchSummary :improvement="improvement" />
      <p class="small text-secondary">Checked on {{ machineText }} and its parts, every severity.</p>
      <div class="table-responsive">
        <table class="table table-sm mb-3">
          <thead>
            <tr><th v-for="(h, i) in table.headers" :key="i" scope="col" :class="{ 'text-end': i > 0 }">{{ h }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in table.rows" :key="r.label">
              <th scope="row" class="fw-normal">{{ r.label }}</th>
              <td class="text-end">{{ r.before }}</td>
              <td class="text-end">{{ r.after }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <template v-if="improvement.can_verify">
        <div class="d-grid gap-2 d-sm-flex">
          <button type="button" class="btn btn-outline-danger btn-lg" @click="emit('verify', 'not_effective')">
            Did not work — analyse again
          </button>
          <button type="button" class="btn btn-success btn-lg" @click="emit('verify', 'effective')">Close: it worked</button>
        </div>
        <p class="small text-secondary mt-2 mb-0"><em>Did not work</em> closes this improvement and starts a new one with the same tickets.</p>
      </template>
      <p v-else-if="waitingForDecision" class="mb-0 fw-semibold">Ready to verify. An engineer or manager of the site decides.</p>
    </div>
  </div>
</template>
