"""Load sample data into an empty dev database, for trying the app by hand.

Goes through the API of the running dev backend (PyCharm "Backend",
DEV_AUTH_BYPASS=1, DEV_STUB_ROLE "admin"), so every record passes the same
checks as one entered in the UI and the script needs no DB credentials.
Run it once after tooling/dev/dev-db-reset.bat; it refuses a database that
already has sites, so it never doubles up data.

Sites and units follow docs/Plant-Facts.md § 2; people, logins and equipment
are made up.  The logins are not Keycloak users: with DEV_AUTH_BYPASS everyone
is the stub user "dev", so they only show how Team looks.  To act as a role,
set DEV_STUB_ROLE (see backend/example_secrets_app.py).

Usage: tooling/dev/dev-seed.bat [base URL, default http://localhost:5001]
"""

import json
import sys
import urllib.error
import urllib.request

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5001").rstrip("/")

SITES = [
    {"code": "SMTW", "name": "Main factory, Pavoorchatram", "address": "10/712, Surandai Road, Pavoorchatram",
     "is_default": True},
    {"code": "BRICKS", "name": "Stock yard 1, Keelathottam"},
    {"code": "SMTW-KP", "name": "Stock yard 2, Keelapavoor"},
    {"code": "AGRI-VKM", "name": "Vettaikarankulam farm"},
    {"code": "AGRI-KDK", "name": "Kadabokaathi farm"},
    {"code": "SSVT", "name": "Sree Shenbaga Vinayagar Tiles (job work)"},
]

# (site code, unit code, name)
UNITS = [
    ("SMTW", "FWMILL", "Firewood processing mill"),
    ("SMTW", "MCC1", "New extrusion and punching line, part 1"),
    ("SMTW", "MCC2", "New extrusion and punching line, part 2"),
    ("SMTW", "KILN", "Kiln"),
    ("BRICKS", "FILTER", "Clay filtration plant"),
    ("SSVT", "SHOP", "Hydraulic press shop"),
]

# (code, name, [type names])
CLASSES = [
    ("VBM", "Vertical blade mill", []),
    ("EXT", "Extruder", ["Vacuum extruder"]),
    ("CMP", "Compressor", ["Screw compressor"]),
    ("HP", "Hydraulic press", []),
    ("PMP", "Pump", ["Bore pump", "Centrifugal pump"]),
    ("GBX", "Gearbox", []),
]

TRADES = ["Mechanical", "Electrical", "Welding", "Instrumentation"]

# name, employment, trades, login (None = no login), [(site, role, units or "all")]
PEOPLE = [
    ("Murugan S", "direct", ["Mechanical"], None, [("SMTW", "maint_technician", ["MCC1", "MCC2"])]),
    ("Selvam R", "direct", ["Mechanical", "Welding"], None, [("SMTW", "maint_technician", ["FWMILL"])]),
    ("Sakthi Electricals", "contractor", ["Electrical"], None, [("SMTW", "maint_technician", "all")]),
    ("Arun K", "contractor", ["Instrumentation"], None, []),
    ("Priya M", "direct", [], "mgr.smtw",
     [("SMTW", "maint_manager", "all"), ("SSVT", "maint_engineer", ["SHOP"])]),
    ("Karthik V", "direct", ["Mechanical"], "eng.smtw", [("SMTW", "maint_engineer", "all")]),
    ("Ganesh P", "direct", ["Electrical"], "tech.mcc", [("SMTW", "maint_technician", ["MCC1", "MCC2"])]),
    ("Lakshmi T", "direct", [], "sup.mcc", [("SMTW", "maint_supervisor", ["MCC1", "MCC2"])]),
    ("Ramesh A", "direct", [], "op.mcc2", [("SMTW", "maint_operator", ["MCC2"])]),
    ("Devi N", "direct", [], "store.smtw", [("SMTW", "maint_storekeeper", "all")]),
]

# unit full code, class, type or None, name, make, model, criticality, [(class, name)] component units
EQUIPMENT = [
    ("SMTW.FWMILL", "VBM", None, "Vertical blade mill", None, None, "B", []),
    ("SMTW.MCC2", "EXT", "Vacuum extruder", "Main extruder", "Haendle GmbH", None, "A",
     [("GBX", "Extruder main gearbox")]),
    ("SMTW.MCC2", "CMP", "Screw compressor", "Screw compressor 1", "Atlas Copco", None, "A", []),
    ("SMTW.MCC2", "CMP", "Screw compressor", "Screw compressor 2", "Atlas Copco", None, "B", []),
    ("BRICKS.FILTER", "PMP", "Bore pump", "Bore well pump", None, None, "C", []),
    ("SSVT.SHOP", "HP", None, "Hydraulic press 1", None, None, "A", []),
]


def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE_URL + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read() or b"null")
    except urllib.error.HTTPError as exc:
        sys.exit(f"{method} {path} failed: {exc.code} {exc.read().decode(errors='replace')}")
    except urllib.error.URLError as exc:
        sys.exit(f"Cannot reach the dev backend at {BASE_URL} ({exc.reason}). Is PyCharm 'Backend' running?")


def main():
    me = call("GET", "/api/auth/me")
    if me.get("role") != "admin":
        sys.exit(f"The dev stub user is {me.get('role')!r}; set DEV_STUB_ROLE to 'admin' (or leave it unset) to seed.")
    if call("GET", "/api/masters/sites?include_inactive=1")["total"]:
        sys.exit("The dev database already has sites. Run tooling/dev/dev-db-reset.bat first.")

    site_ids = {s["code"]: call("POST", "/api/masters/sites", s)["id"] for s in SITES}
    unit_ids = {}
    for site, code, name in UNITS:
        unit_ids[f"{site}.{code}"] = call("POST", "/api/masters/units",
                                          {"site_id": site_ids[site], "code": code, "name": name})["id"]

    class_ids, type_ids = {}, {}
    for code, name, types in CLASSES:
        class_ids[code] = call("POST", "/api/masters/equipment-classes", {"code": code, "name": name})["id"]
        for type_name in types:
            type_ids[type_name] = call("POST", "/api/masters/equipment-types",
                                       {"class_id": class_ids[code], "name": type_name})["id"]

    trade_ids = {name: call("POST", "/api/masters/trades", {"name": name})["id"] for name in TRADES}

    for name, employment, trades, login, roles in PEOPLE:
        sites = [{"site_id": site_ids[site], "role": role, "all_units": units == "all",
                  "unit_ids": [] if units == "all" else [unit_ids[f"{site}.{u}"] for u in units]}
                 for site, role, units in roles]
        body = {"name": name, "employment": employment, "trade_ids": [trade_ids[t] for t in trades]}
        if login:
            # A login is saved together with the person's whole set of sites (S011 A1)
            call("POST", "/api/masters/people", {**body, "username": login, "sites": sites})
            continue
        person_id = call("POST", "/api/masters/people", body)["id"]
        for row in sites:   # people without a login get their (Technician) sites one by one
            site_id = row.pop("site_id")
            call("PUT", f"/api/masters/people/{person_id}/sites/{site_id}", row)

    for unit, cls, type_name, name, make, model, criticality, parts in EQUIPMENT:
        body = {"level": "equipment", "unit_id": unit_ids[unit], "class_id": class_ids[cls],
                "name": name, "criticality": criticality}
        if type_name:
            body["type_id"] = type_ids[type_name]
        if make:
            body["make"] = make
        if model:
            body["model"] = model
        node = call("POST", "/api/equipment/", body)
        for part_class, part_name in parts:
            call("POST", "/api/equipment/", {"level": "component_unit", "parent_id": node["id"],
                                             "class_id": class_ids[part_class], "name": part_name})

    print(f"Seeded {len(SITES)} sites, {len(UNITS)} units, {len(CLASSES)} classes, {len(TRADES)} trades, "
          f"{len(PEOPLE)} people, {len(EQUIPMENT)} equipment.")


if __name__ == "__main__":
    main()
