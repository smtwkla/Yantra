"""The browser tests' seed (S024 § 5.2): loaded through the e2e backend's API at the start of
every run (frontend/e2e/setup/global-setup.js), with the admin test headers.

Sites SMTW and BRICKS with their units, and the classes, trades, manufacturers and models,
come from tooling/dev/seed_dev.py; the people and the equipment are the e2e suite's own.
The failure codes (S016) come with the migrations.

Each person acts in the browser as X-Test-Role: maintenance_team, X-Test-User: <login>, so
their real memberships in the database decide what they may do, as in production.  The
browser side (frontend/e2e/support/people.js) names them by the same keys.

Usage: seed_e2e.py [base URL, default http://127.0.0.1:5002]
"""

import functools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dev"))

import seed_dev  # noqa: E402  (after the path above)

DEFAULT_BASE_URL = "http://127.0.0.1:5002"
ADMIN_HEADERS = {"X-Test-Role": "admin", "X-Test-User": "e2e_admin"}
SITE_CODES = ("SMTW", "BRICKS")

# key, login (None = no login), name, trades, [(site, role, units or "all")].  The roles are
# the site roles (config_rbac.SITE_ROLES).
PEOPLE = [
    ("operator", "e2e_operator", "Muthu (operator)", [], [("SMTW", "maint_operator", ["MCC2"])]),
    ("supervisor", "e2e_supervisor", "Selvi (supervisor)", [], [("SMTW", "maint_supervisor", ["MCC1", "MCC2"])]),
    ("technician", "e2e_technician", "Kannan (technician)", ["Mechanical"], [("SMTW", "maint_technician", "all")]),
    ("technician2", "e2e_technician2", "Ravi (technician)", ["Electrical"], [("SMTW", "maint_technician", "all")]),
    ("engineer", "e2e_engineer", "Priya (engineer)", [], [("SMTW", "maint_engineer", "all")]),
    ("manager", "e2e_manager", "Arun (manager)", [],
     [("SMTW", "maint_manager", "all"), ("BRICKS", "maint_manager", "all")]),
    ("storekeeper", "e2e_storekeeper", "Devi (storekeeper)", [], [("SMTW", "maint_storekeeper", "all")]),
    # No phone: picked as "found by" and "who did the work", never acts (BR2-03)
    ("operator_nologin", None, "Ramesh (operator, no phone)", [], [("SMTW", "maint_operator", ["MCC2"])]),
]

# IT admin holds a token role (it_admin), not a site role: no Team record is needed
IT_ADMIN = ("it_admin", "e2e_it_admin", "IT admin")

# In the shape of seed_dev.EQUIPMENT: unit, model key, name, criticality, [(model key, name)].
# The codes are generated (S002), so the tests find these by name (frontend/e2e/support/people.js).
EQUIPMENT = [
    ("SMTW.MCC2", "HAENDLE", "E2E extruder", "A", [("GEN-GBX", "E2E extruder gearbox")]),
    ("SMTW.MCC2", "GA37", "E2E scrapped compressor", "C", []),
    ("SMTW.MCC1", "GEN-VBM", "E2E MCC1 mill", "B", []),
    ("BRICKS.FILTER", "GEN-PMP", "E2E filter pump", "C", []),
]
SCRAPPED = "E2E scrapped compressor"


def display_names():
    """login -> name, for the top bar (the e2e backend's user factory)."""
    names = {login: name for _key, login, name, _trades, _roles in PEOPLE if login}
    names[IT_ADMIN[1]] = IT_ADMIN[2]
    return names


def main():
    base_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL).rstrip("/")
    api = functools.partial(seed_dev.call, base_url=base_url, headers=ADMIN_HEADERS)

    me = api("GET", "/api/auth/me")
    if me.get("role") != "admin":
        sys.exit(f"The seed must act as admin, but the backend says {me.get('role')!r}.")
    if api("GET", "/api/masters/sites?include_inactive=1")["total"]:
        sys.exit("The e2e database already has sites: the e2e backend did not start from an empty database.")

    sites = [s for s in seed_dev.SITES if s["code"] in SITE_CODES]
    units = [u for u in seed_dev.UNITS if u[0] in SITE_CODES]
    ids = seed_dev.create_masters(api, sites, units)
    seed_dev.create_people(api, [(name, "direct", trades, login, roles)
                                 for _key, login, name, trades, roles in PEOPLE], ids)
    nodes = seed_dev.create_equipment(api, EQUIPMENT, ids)
    api("PUT", f"/api/equipment/{nodes[SCRAPPED]['id']}", {"status": "scrapped"})

    print(f"e2e seed: {len(sites)} sites, {len(units)} units, {len(PEOPLE)} people, {len(nodes)} equipment nodes.")


if __name__ == "__main__":
    main()
