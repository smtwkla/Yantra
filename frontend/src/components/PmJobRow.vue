<script setup>
/**
 * One PM job as a row (docs/steps/S098-pm-job-phone/1-brief.md § 5.9), shared by the PM list and *Me* › *Open
 * work*: the badges (In progress, Done with On time / Late, or the standing), the serial, the due point or the
 * done date, the machine, the plan, and a small line (the unit, the meter, who). The row opens the job page.
 * The class `job-row` and `data-equipment` stay as S097 had them: the browser tests find rows by them.
 *
 * S099 § 5.7: a job waiting for verification shows *To verify*, its done time (a queue is read by time) and its
 * findings; a verified one *Verified* and "Verified by …"; a sent-back one *Sent back* after *In progress*.
 *
 * S101 § 5.8: a rescheduled job shows *Rescheduled* after its badges; a skipped one *Skipped*, its skip date and
 * who skipped it.
 */
import { computed } from "vue";
import { formatDate, formatDateTime } from "../utils/datetime";
import { assigneeText, daysPastText, dueText, findingsText, jobBadges, meterNowText } from "../utils/pmLabels";

const props = defineProps({
  job: { type: Object, required: true },
});

const done = computed(() => props.job.state === "done" || props.job.state === "verified");
const started = computed(() => props.job.state === "in_progress");
const skipped = computed(() => props.job.state === "skipped");

const rightText = computed(() => {
  const job = props.job;
  if (job.awaits_verification) return `Done ${formatDateTime(job.done_at)}`;
  if (done.value) return `Done ${formatDate(job.done_at)}`;
  if (skipped.value) return `Skipped ${formatDate(job.done_at)}`;
  return `${dueText(job.due_on, job.due_meter, job.meter?.meter_type)}${daysPastText(job.days_past)}`;
});
const itemCount = computed(() => `${props.job.plan.item_count} ${props.job.plan.item_count === 1 ? "item" : "items"}`);
const smallLine = computed(() => {
  const job = props.job;
  if (skipped.value) return [job.unit.full_code, job.skipped && `by ${job.skipped.by_name}`].filter(Boolean).join(" · ");
  if (done.value) {
    const findings = job.awaits_verification ? findingsText(job.findings) : "";
    return [job.unit.full_code, findings, job.performed_by && `by ${job.performed_by.name}`,
      job.verification && `Verified by ${job.verification.by_name}`].filter(Boolean).join(" · ");
  }
  const who = started.value && job.performed_by ? `In progress · ${job.performed_by.name}` : assigneeText(job);
  return [job.unit.full_code, meterNowText(job.meter), who].filter(Boolean).join(" · ");
});
</script>

<template>
  <router-link
    :to="`/pm/jobs/${job.id}`"
    class="list-group-item list-group-item-action job-row"
    :data-equipment="job.equipment.code"
  >
    <span class="d-flex flex-wrap justify-content-between align-items-baseline gap-2">
      <span>
        <span v-for="b in jobBadges(job)" :key="b.label" class="badge me-1" :class="b.badge">{{ b.label }}</span>
        <span class="small text-secondary ms-1">{{ job.serial }}</span>
      </span>
      <span class="small">{{ rightText }}</span>
    </span>
    <span class="d-block fw-semibold">{{ job.equipment.code }} — {{ job.equipment.name }}</span>
    <span class="d-block">{{ job.plan.title }} · {{ itemCount }}</span>
    <span class="d-block small text-secondary">{{ smallLine }}</span>
  </router-link>
</template>

<style scoped>
.job-row {
  min-height: 44px;
  overflow-wrap: anywhere;
}
</style>
