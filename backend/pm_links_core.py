"""PM template links — the pure rules (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.3, § 5.4; R03.18).  No
DB, no Flask, no clock.

The work of a PM plan lives on its template; a machine has a plan row per template that reaches it.  This module
answers, from plain data the shell reads:

- which templates reach a node (``reaching_templates``: in S104 the active links to the node itself; R03.19 adds
  class, type and model);
- what to do with the node's plan rows (``plan_actions``: make, relink, unlink; a row is never deleted, D3);
- which meter types a template needs on a machine (``needed_meters``: the trigger's and each *Meter reading* item's,
  each once);
- which node's meter each need uses (``resolve_meters``: the node's own meter in force, else the node's meter link
  in use (S104 A1: a link set on the part's Meters card names its parent's or grandparent's meter); nothing walks
  up the tree), and whether the template applies (``applies``: the types missing);
- why a plan makes no job (``stop_remark``), in a fixed order.

Two SQL texts live here because they state these rules over the tables, and both pm_jobs.py and equipment.py use
them (as contracts_core holds SQL that equipment.py uses): ``IN_FORCE_SQL`` (a plan in force) and
``LINK_PLANS_SQL`` (the plans in force that use a meter link: ``needed_meters``' rule as SQL).

A bad input is a shell bug, never user input: it raises ``TypeError`` naming it (S095 D8).
"""

from pm_jobs_core import TEMPLATE_INACTIVE_REMARK, UNLINKED_REMARK, does_not_apply_remark, not_for_machine_remark
from pm_schedule_core import BOTH, METER

CLASS, TYPE, MODEL, EQUIPMENT = "class", "type", "model", "equipment"
TARGET_KINDS = (CLASS, TYPE, MODEL, EQUIPMENT)   # pm_template_links.target_kind's ENUM order
METER_READING = "meter"                            # pm_template_items.reading_kind of an item that logs a meter

# S104 § 4.2: a plan in force (linked, not *Not for this machine*, its template active), as SQL over pl and tp
IN_FORCE_SQL = "(pl.linked = 1 AND pl.not_for_machine = 0 AND tp.active = 1)"
# S104 A1.6.5: the plans in force of each link's part whose template names the link's meter type as its trigger or
# in an active Meter reading item -> rows (link_id, name, code), by name.  ``{ids}`` takes the link ids' marks.
# The same rule as needed_meters; test_meters_api checks the two agree.
LINK_PLANS_SQL = (
    "SELECT l.id AS link_id, tp.name, pe.code FROM node_meter_links l"
    " JOIN pm_plans pl ON pl.equipment_id = l.equipment_id"
    " JOIN pm_templates tp ON tp.id = pl.template_id"
    " JOIN equipment pe ON pe.id = pl.equipment_id"
    f" WHERE l.id IN ({{ids}}) AND {IN_FORCE_SQL} AND ("
    f"  (tp.trigger_kind IN ('{METER}', '{BOTH}') AND tp.meter_type_id = l.meter_type_id)"
    "   OR EXISTS (SELECT 1 FROM pm_template_items i WHERE i.template_id = tp.id AND i.active = 1"
    f"   AND i.reading_kind = '{METER_READING}' AND i.meter_type_id = l.meter_type_id))"
    " ORDER BY tp.name, pe.code, l.id"
)


def _flag(value, key):
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be a bool, not {type(value).__name__}")
    return value


def reaching_templates(node, links):
    """The ids of the templates that reach ``node`` ({id, class_id, type_id, model_id}) through ``links`` (rows with
    template_id, target_kind, target_id, active) -> a sorted list, each once.  S104: only an active ``equipment``
    link naming the node; R03.19 adds the class, type and model links (and *Not for this machine*)."""
    return sorted({link["template_id"] for link in links
                   if link["active"] and link["target_kind"] == EQUIPMENT and link["target_id"] == node["id"]})


def plan_actions(reaching_ids, plans):
    """The node's plan rows against the templates that reach it (§ 5.4) -> ``{make: [template ids], relink: [plan
    ids], unlink: [plan ids]}``, each sorted.  ``plans`` are the node's rows ({id, template_id, linked}).  A reaching
    template without a row is made; an unlinked row whose template reaches is relinked; a linked row whose template
    no longer reaches is unlinked.  A row is never deleted (D3)."""
    reaching = set(reaching_ids)
    have = {plan["template_id"] for plan in plans}
    return {
        "make": sorted(reaching - have),
        "relink": sorted(plan["id"] for plan in plans if not plan["linked"] and plan["template_id"] in reaching),
        "unlink": sorted(plan["id"] for plan in plans if plan["linked"] and plan["template_id"] not in reaching),
    }


def needed_meters(template, items):
    """The meter types ``template`` ({trigger_kind, meter_type_id}) and its active ``items`` (rows with item_type,
    reading_kind, meter_type_id; in position order) need on a machine (A1.6.2) -> the meter type ids in the order
    first named: the trigger's, then the items'; a type named twice is one need."""
    needs = []
    if template["trigger_kind"] in (METER, BOTH):
        needs.append(template["meter_type_id"])
    for item in items:
        if item.get("reading_kind") == METER_READING and item.get("meter_type_id") is not None:
            needs.append(item["meter_type_id"])
    return list(dict.fromkeys(needs))


def resolve_meters(needs, node_id, types_by_node, links):
    """The node whose meter each need uses (A1.6.2) -> ``{meter_type_id: node id or None}``.  ``types_by_node``
    maps a node id to the set of meter type ids in force on it (meters_core.effective_meters); ``links`` is
    ``{meter_type_id: source node id}`` of the node's meter links in use (meters_core.link_states).  The node itself
    when it has the type in force, else the source of its link of that type, else None."""
    own = types_by_node.get(node_id, ())
    return {type_id: node_id if type_id in own else links.get(type_id) for type_id in needs}


def applies(needs, resolved):
    """The types of ``needs`` that ``resolved`` (resolve_meters') found no meter for, in the needs' order; empty
    when the template applies on the machine."""
    return [type_id for type_id in needs if resolved.get(type_id) is None]


def missing_text(type_names, node_code):
    """"no Run hours meter on HP003", "no Run hours or Oil temperature meter on HP003", "no A, B or C meter on …"."""
    names = list(type_names)
    joined = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} or {names[-1]}"
    return f"no {joined} meter on {node_code}"


def stop_remark(template_active, linked, not_for_machine, missing_type_names, node_code, not_for_reason=None):
    """Why a plan makes no job now (§ 5.4) -> the remark, or None when the plan is in force and its template applies.
    In this order: the template deactivated, the template removed from the machine, *Not for this machine* (R03.19),
    a needed meter missing on the machine (its type names in the template's order)."""
    if not _flag(template_active, "template_active"):
        return TEMPLATE_INACTIVE_REMARK
    if not _flag(linked, "linked"):
        return UNLINKED_REMARK
    if _flag(not_for_machine, "not_for_machine"):
        return not_for_machine_remark(not_for_reason)
    if missing_type_names:
        return does_not_apply_remark(missing_text(missing_type_names, node_code))
    return None
