<script setup>
/**
 * The PM card on the equipment page (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.10, mock-up 11; S096
 * before it): the plans of the node and its parts, each with its template's name, its source ("This machine"), the
 * trigger in words, and the open job or the next due, or why it makes no job ("Does not apply: no Run hours meter on
 * HP003"). A row opens the plan's page; *Attach PM template* (editors, `can_add`) opens the attach dialog.
 *
 * It loads its own list (`GET /api/pm/plans?equipment_id=`), as LessonsCard does. It shows nothing for a reader of
 * a machine with no plan (no empty box on the floor); an editor always sees it. Plans removed from the machine sit
 * behind *Not in use (n)*, for every reader (history, not a secret). The header counts the linked plans (BR1-14).
 *
 * S097: each plan's row gains one line from its `schedule`: the open job (badge, serial, due) or, without one,
 * "Next due …". `schedule` is null for a reader without pm_job:read at the node's site (the storekeeper): no line.
 */
import { computed, ref, watch } from "vue";
import { apiGet } from "../../api";
import {
  daysPastText, dueText, jobBadges, meterNowText, nextDueText, planSubline, planTitle,
} from "../../utils/pmLabels";
import PmAttachDialog from "./PmAttachDialog.vue";

const props = defineProps({
  node: { type: Object, required: true },
});

const plans = ref(null); // {items, unlinked, can_add}; null while loading
const loadError = ref("");
const showUnlinked = ref(false);
const attachDialog = ref(null);
let loadSeq = 0;

const visible = computed(() => {
  if (loadError.value) return true;
  const p = plans.value;
  return Boolean(p) && (p.items.length > 0 || p.unlinked.length > 0 || p.can_add);
});

async function load() {
  const seq = ++loadSeq;
  loadError.value = "";
  try {
    const loaded = await apiGet(`/api/pm/plans?equipment_id=${props.node.id}`);
    if (seq === loadSeq) plans.value = loaded;
  } catch (err) {
    if (seq === loadSeq) loadError.value = err.message;
  }
}

// Vue Router reuses the page when only :id changes
watch(() => props.node.id, () => {
  plans.value = null;
  showUnlinked.value = false;
  load();
}, { immediate: true });

// S097 § 5.10: "PM-2026-11-004 · 29-11-2026 · 3 days ago", then the meter now for a meter plan
function openJobText(schedule) {
  const job = schedule.open_job;
  const due = dueText(job.due_on, job.due_meter, schedule.meter?.meter_type);
  return [job.serial, `${due}${daysPastText(job.days_past)}`, meterNowText(schedule.meter)].filter(Boolean)
    .join(" · ");
}

// S104 A1: the page reloads the card after a meter or meter link write, so "Does not apply" shows at once
defineExpose({ load });
</script>

<template>
  <div class="order-0">
    <div v-if="visible" class="card mb-3" data-testid="pm-card">
      <div class="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
        <span>PM plans<template v-if="plans"> ({{ plans.items.length }})</template></span>
        <button v-if="plans?.can_add" type="button" class="btn btn-sm btn-primary tap-target" @click="attachDialog.open()">
          <i class="fa-solid fa-plus me-1"></i>Attach PM template
        </button>
      </div>
      <div v-if="loadError" class="card-body text-danger">PM plans could not be loaded: {{ loadError }}</div>
      <template v-else>
        <div v-if="plans.items.length === 0 && plans.can_add" class="card-body text-secondary">
          No PM plans yet. Attach a PM template to plan the work.
        </div>
        <div class="list-group list-group-flush">
          <router-link
            v-for="p in [...plans.items, ...(showUnlinked ? plans.unlinked : [])]"
            :key="p.id"
            :to="`/equipment/pm/${p.id}`"
            class="list-group-item list-group-item-action plan-row"
            :class="{ 'text-secondary': !p.linked || p.stop_remark }"
            :data-plan="p.template.name"
          >
            <span class="d-block fw-semibold">{{ planTitle(p) }}</span>
            <span class="d-block">{{ p.linked ? p.source.label : "Removed from this machine" }} · {{ p.trigger_text }}</span>
            <span class="d-block small text-secondary">{{ planSubline(p) }}</span>
            <!-- A started job of a stopped plan is still shown: it can be finished -->
            <span v-if="p.linked && p.schedule?.open_job" class="d-block small" data-testid="pm-open-job">
              <span v-for="b in jobBadges(p.schedule.open_job)" :key="b.label" class="badge me-1" :class="b.badge">
                {{ b.label }}
              </span>
              {{ openJobText(p.schedule) }}
            </span>
            <span v-else-if="p.linked && p.stop_remark" class="d-block small" data-testid="pm-stop-remark">{{ p.stop_remark }}</span>
            <span v-else-if="p.linked && p.schedule?.next_due" class="d-block small" data-testid="pm-next-due">
              {{ nextDueText(p.schedule.next_due, p.schedule.meter) }}
            </span>
          </router-link>
        </div>
        <div v-if="plans.unlinked.length" class="card-footer">
          <button type="button" class="btn btn-link p-0 tap-target" :aria-expanded="showUnlinked" @click="showUnlinked = !showUnlinked">
            Not in use ({{ plans.unlinked.length }})
          </button>
        </div>
      </template>
    </div>
    <PmAttachDialog v-if="plans?.can_add" ref="attachDialog" :node="node" @saved="load" />
  </div>
</template>

<style scoped>
.plan-row {
  overflow-wrap: anywhere;
}
</style>
