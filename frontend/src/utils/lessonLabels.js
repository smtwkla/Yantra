/**
 * Words and bounds of the one-point lesson screens (docs/steps/S077-one-point-lesson-screens/1-brief.md § 3).
 * The lesson's own title and text are the writer's (Tamil or English); these are the screen's words.
 */
import { formatDate } from "./datetime";

// The bounds the server enforces (S075 § 5.2); the screen's maxlength and counters follow them
export const LESSON_TITLE_MAX = 80;
export const LESSON_BODY_MAX = 1000;

/** "Every Hydraulic press": the badge on a lesson that comes from the class. */
export function classBadgeText(cls) {
  return `Every ${cls.name}`;
}

/**
 * The lesson page's first line: "HP003 — Hydraulic press 3 · for every Hydraulic press"; the class
 * only ("For every Hydraulic press") when the machine is outside the reader's units; the machine
 * only for a machine lesson.
 */
export function lessonTargetText(lesson) {
  const machine = lesson.machine ? `${lesson.machine.code} — ${lesson.machine.name}` : "";
  const cls = lesson.class ? `for every ${lesson.class.name}` : "";
  if (machine && cls) return `${machine} · ${cls}`;
  if (cls) return `${cls[0].toUpperCase()}${cls.slice(1)}`;
  return machine;
}

/** "30-10-2026": the date the lesson was written. */
export function lessonDate(createdAt) {
  return formatDate(createdAt);
}

/** The words of the class tick; the class name is unknown when the read of the machine failed. */
export function classTickLabel(className) {
  return className ? `Show on every machine of class ${className}` : "Show on every machine of this machine's class";
}
