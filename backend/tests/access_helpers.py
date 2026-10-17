"""Shared by the tests that give people site roles (S011)."""


def site_rows(role, units):
    """The ``sites`` body for a role at the units' sites, grouped by site, chosen units."""
    by_site = {}
    for unit in units:
        by_site.setdefault(unit["site_id"], []).append(unit["id"])
    return [{"site_id": site_id, "role": role, "all_units": False, "unit_ids": ids} for site_id, ids in by_site.items()]
