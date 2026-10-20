"""Printable asset list — the pure rules (docs/steps/S015-asset-list/1-brief.md).

Groups machines by unit and puts each machine's parts under it, depth-first, so the
printed page can run down the list.  The # counts machines only (the accounts compare the
last # with their machine count).

No database, no Flask: plain data in, plain data out.
"""

from equipment_core import SCRAPPED

MAX_ASSET_LIST_ROWS = 3000
TOO_MANY_ROWS = "Too many rows — narrow the list by site or unit"

MACHINE_DEPTH = 0


def build_asset_list(machines, parts, include_scrapped):
    """``(result, None)`` or ``(None, TOO_MANY_ROWS)``.

    ``machines``: dicts with id, code, site_code, site_name, unit_code, unit_name (plus any
    display fields, which are passed through).  ``parts``: dicts with id, parent_id, code,
    status.  ``result`` is ``{units: [{site_code, site_name, unit_code, unit_name, rows,
    machine_count, part_count}], total_rows}``.  Each row is the input dict plus ``depth``
    (0 for the machine, then +1 per level below it: a component-unit, or a component fitted
    directly to the machine, is 1; a component in a component-unit is 2) and ``number`` (running machine number in the
    unit; None for parts).  Scrapped parts are dropped unless ``include_scrapped``; a part
    whose machine is not in ``machines`` is ignored."""
    children = {}
    for part in parts:
        if include_scrapped or part["status"] != SCRAPPED:
            children.setdefault(part["parent_id"], []).append(part)
    for group in children.values():
        group.sort(key=lambda r: r["code"])

    by_unit = {}
    for machine in sorted(machines, key=lambda r: r["code"]):
        by_unit.setdefault((machine["site_code"], machine["unit_code"]), []).append(machine)

    units, total = [], 0
    for (site_code, unit_code), unit_machines in sorted(by_unit.items()):
        rows, part_count = [], 0
        for number, machine in enumerate(unit_machines, start=1):
            rows.append({**machine, "depth": MACHINE_DEPTH, "number": number})
            for part, depth in _parts_depth_first(children, machine["id"], MACHINE_DEPTH + 1):
                rows.append({**part, "depth": depth, "number": None})
                part_count += 1
        first = unit_machines[0]
        units.append({"site_code": site_code, "site_name": first["site_name"], "unit_code": unit_code,
                      "unit_name": first["unit_name"], "rows": rows,
                      "machine_count": len(unit_machines), "part_count": part_count})
        total += len(rows)
        if total > MAX_ASSET_LIST_ROWS:
            return None, TOO_MANY_ROWS
    return {"units": units, "total_rows": total}, None


def _parts_depth_first(children, parent_id, depth):
    for part in children.get(parent_id, []):
        yield part, depth
        yield from _parts_depth_first(children, part["id"], depth + 1)
