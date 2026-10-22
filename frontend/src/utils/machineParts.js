/**
 * The parts of a ticket's machine, as select rows (S020 BR1-09; extracted from
 * EditTicketDialog.vue, S018 BR3-11): the ticket edit's *Part* and the parts line's *Fitted to*.
 *
 * The parts come from the machine's equipment detail (`children`, two levels), the scrapped ones
 * left out, each labelled "CODE name", a part one level further down indented with "— ".
 */
import { apiGet } from "../api";

/** The equipment detail's `children` (two levels) -> [{id, label}], scrapped ones left out. */
export function partRows(children, depth = 0) {
  return (children ?? []).flatMap((child) => (child.status === "scrapped" ? [] : [
    { id: child.id, label: `${"— ".repeat(depth)}${child.code} ${child.name}` },
    ...partRows(child.children, depth + 1),
  ]));
}

/** The machine's parts -> [{id, label}] (GET /api/equipment/<machine>). */
export async function loadMachineParts(machineId) {
  return partRows((await apiGet(`/api/equipment/${machineId}`)).children);
}

/**
 * `rows` with the current choice `node` ({id, code, name}) first when it is not listed (scrapped
 * since), so an untouched field never clears it -> a new array.
 */
export function keepChoice(rows, node) {
  if (!node || rows.some((row) => row.id === node.id)) return rows;
  return [{ id: node.id, label: `${node.code} ${node.name}` }, ...rows];
}
