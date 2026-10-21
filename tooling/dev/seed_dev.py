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

import functools
import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:5001"

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

# Manufacturers (S012): makers, plus "Generic" (maker unknown) and our own designs
MANUFACTURERS = ["Haendle GmbH", "Atlas Copco", "Generic", "SMTW (in-house)"]

# key, manufacturer, designation, class, type or None.  The designations of the Haendle and
# in-house models are made up; Generic models are named by what they are (S012 § 4.1).
MODELS = [
    ("GA37", "Atlas Copco", "GA37", "CMP", "Screw compressor"),
    ("HAENDLE", "Haendle GmbH", "VAH 600", "EXT", "Vacuum extruder"),
    ("HYP", "SMTW (in-house)", "SMTW-HYP-01", "HP", None),
    ("GEN-VBM", "Generic", "Generic vertical blade mill", "VBM", None),
    ("GEN-PMP", "Generic", "Generic bore pump", "PMP", "Bore pump"),
    ("GEN-GBX", "Generic", "Generic gearbox", "GBX", None),
]

# unit full code, model key, name, criticality, [(model key, name)] component units.
# Class and type come from the model (S012).
EQUIPMENT = [
    ("SMTW.FWMILL", "GEN-VBM", "Vertical blade mill", "B", []),
    ("SMTW.MCC2", "HAENDLE", "Main extruder", "A", [("GEN-GBX", "Extruder main gearbox")]),
    ("SMTW.MCC2", "GA37", "Screw compressor 1", "A", []),
    ("SMTW.MCC2", "GA37", "Screw compressor 2", "B", []),
    ("BRICKS.FILTER", "GEN-PMP", "Bore well pump", "C", []),
    ("SSVT.SHOP", "HYP", "Hydraulic press 1", "A", []),
]


def call(method, path, body=None, *, base_url, headers=None):
    """One API call; the JSON answer, or exit with the refusal.  ``headers`` are added to
    the JSON content type (the browser tests' seed sends its test identity, S024)."""
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base_url + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read() or b"null")
    except urllib.error.HTTPError as exc:
        sys.exit(f"{method} {path} failed: {exc.code} {exc.read().decode(errors='replace')}")
    except urllib.error.URLError as exc:
        sys.exit(f"Cannot reach the backend at {base_url} ({exc.reason}). Is it running?")


def create_masters(api, sites, units):
    """The sites and units given, and every class, type, manufacturer, model and trade above.
    ``api`` is ``call`` with its base URL (and headers) bound.  Returns the new ids by key:
    sites by code, units by "SITE.UNIT", classes by code, types by name, models by key,
    trades by name."""
    site_ids = {s["code"]: api("POST", "/api/masters/sites", s)["id"] for s in sites}
    unit_ids = {}
    for site, code, name in units:
        unit_ids[f"{site}.{code}"] = api("POST", "/api/masters/units",
                                         {"site_id": site_ids[site], "code": code, "name": name})["id"]

    class_ids, type_ids = {}, {}
    for code, name, types in CLASSES:
        class_ids[code] = api("POST", "/api/masters/equipment-classes", {"code": code, "name": name})["id"]
        for type_name in types:
            type_ids[type_name] = api("POST", "/api/masters/equipment-types",
                                      {"class_id": class_ids[code], "name": type_name})["id"]

    maker_ids = {name: api("POST", "/api/masters/manufacturers", {"name": name})["id"] for name in MANUFACTURERS}
    model_ids = {}
    for key, maker, designation, cls, type_name in MODELS:
        model_ids[key] = api("POST", "/api/masters/equipment-models", {
            "manufacturer_id": maker_ids[maker], "designation": designation, "class_id": class_ids[cls],
            "type_id": type_ids[type_name] if type_name else None})["id"]

    trade_ids = {name: api("POST", "/api/masters/trades", {"name": name})["id"] for name in TRADES}
    return {"sites": site_ids, "units": unit_ids, "classes": class_ids, "types": type_ids,
            "models": model_ids, "trades": trade_ids}


def create_people(api, people, ids):
    """``people`` in the shape of PEOPLE; ``ids`` from create_masters."""
    for name, employment, trades, login, roles in people:
        sites = [{"site_id": ids["sites"][site], "role": role, "all_units": units == "all",
                  "unit_ids": [] if units == "all" else [ids["units"][f"{site}.{u}"] for u in units]}
                 for site, role, units in roles]
        body = {"name": name, "employment": employment, "trade_ids": [ids["trades"][t] for t in trades]}
        if login:
            # A login is saved together with the person's whole set of sites (S011 A1)
            api("POST", "/api/masters/people", {**body, "username": login, "sites": sites})
            continue
        person_id = api("POST", "/api/masters/people", body)["id"]
        for row in sites:   # people without a login get their (Technician) sites one by one
            site_id = row.pop("site_id")
            api("PUT", f"/api/masters/people/{person_id}/sites/{site_id}", row)


def create_equipment(api, equipment, ids):
    """``equipment`` in the shape of EQUIPMENT; returns the new nodes (machines and their
    component units) by name."""
    nodes = {}
    for unit, model, name, criticality, parts in equipment:
        nodes[name] = api("POST", "/api/equipment/", {"level": "equipment", "unit_id": ids["units"][unit],
                                                      "model_id": ids["models"][model], "name": name,
                                                      "criticality": criticality})
        for part_model, part_name in parts:
            nodes[part_name] = api("POST", "/api/equipment/", {
                "level": "component_unit", "parent_id": nodes[name]["id"],
                "model_id": ids["models"][part_model], "name": part_name})
    return nodes


def main():
    base_url = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL).rstrip("/")
    api = functools.partial(call, base_url=base_url)

    me = api("GET", "/api/auth/me")
    if me.get("role") != "admin":
        sys.exit(f"The dev stub user is {me.get('role')!r}; set DEV_STUB_ROLE to 'admin' (or leave it unset) to seed.")
    if api("GET", "/api/masters/sites?include_inactive=1")["total"]:
        sys.exit("The dev database already has sites. Run tooling/dev/dev-db-reset.bat first.")

    ids = create_masters(api, SITES, UNITS)
    create_people(api, PEOPLE, ids)
    create_equipment(api, EQUIPMENT, ids)

    print(f"Seeded {len(SITES)} sites, {len(UNITS)} units, {len(CLASSES)} classes, {len(MANUFACTURERS)} "
          f"manufacturers, {len(MODELS)} models, {len(TRADES)} trades, {len(PEOPLE)} people, "
          f"{len(EQUIPMENT)} equipment.")


if __name__ == "__main__":
    main()
