"""The tour's standard data on lane 9 (after seed_e2e.py): realistic machines, meters, readings,
tickets, an improvement, a lesson, a contract and PM plans/jobs in every state, made through the API
as each role (S103).  tour.py calls main(); the ids go to scratch/help-shots/data.json."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tooling" / "e2e"))
os.environ.setdefault("E2E_LANE", "9")
import e2e_backend  # noqa: E402  (reads E2E_LANE at import)
import run_lanes  # noqa: E402

OUT = ROOT / "scratch" / "help-shots"
BASE = "http://127.0.0.1:5019"
IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(IST).replace(second=0, microsecond=0)
TOKEN_ROLE = {"admin": "admin", "it_admin": "it_admin"}
PHOTO = OUT / "files" / "sight-glass.jpg"     # made by make_photo.py before this runs
LANE_DATABASE = run_lanes.lane_database(9)


def headers(who):
    h = {"X-Test-Role": TOKEN_ROLE.get(who, "maintenance_team"), "X-Test-User": f"e2e_{who}"}
    if who == "manager":
        h["X-Test-Email"] = "e2e_manager@example.test"
    return h


def api(who, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **headers(who)})
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read() or b"null")
    except urllib.error.HTTPError as exc:
        sys.exit(f"{who} {method} {path} {body} failed: {exc.code} {exc.read().decode(errors='replace')}")


def upload(who, path, fields, file_path):
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"photo.jpg\"\r\n"
                  "Content-Type: image/jpeg\r\n\r\n").encode() + file_path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(BASE + path, data=b"".join(parts), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}", **headers(who)})
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"upload {path} failed: {exc.code} {exc.read().decode(errors='replace')}")


def sql(statement):
    subprocess.run([*run_lanes.COMPOSE, "exec", "-T", "mariadb", "mariadb", "-uroot",
                    f"-p{run_lanes.DEV_ROOT_PASSWORD}", LANE_DATABASE, "-e", statement], check=True)


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M")


def day(offset):
    return (NOW + timedelta(days=offset)).date().isoformat()


def items(path, who="admin"):
    return api(who, "GET", path)["items"]


def touch_ups():
    """Three changes no API allows, as SQL on the lane database only (S103 BR1-06): the seed people's names
    lose their " (role)" ending, so a screen shows "Kannan", not "Kannan (technician) (Technician)"; the
    seed's scrapped compressor gets a plant name; the seed's overdue ticket gets a plant description.
    Everything else of the tour's data is made through the API."""
    # check_target gets the lane's own name, so it refuses only if LANE_DATABASE loses its _e2e ending
    refusal = e2e_backend.check_target({"host": "127.0.0.1", "database": LANE_DATABASE})
    if refusal:
        sys.exit(f"setup_tour: {refusal}")
    sql("UPDATE people SET name = TRIM(SUBSTRING_INDEX(name, ' (', 1)) WHERE name LIKE '% (%'")
    sql("UPDATE equipment SET name = 'Old reciprocating compressor' WHERE name = 'E2E scrapped compressor'")
    sql("UPDATE tickets SET description = 'Mill bearing noisy. Waiting for bearing 6310 from the store.'"
        " WHERE description = 'E2E seed: overdue for parts'")


def main():
    touch_ups()
    me = {k: api(k, "GET", "/api/auth/me")["person_id"] for k in
          ("operator", "supervisor", "technician", "technician2", "engineer", "manager", "storekeeper")}
    units = {u["full_code"]: u["id"] for u in items("/api/masters/units")}
    models = {m["designation"]: m["id"] for m in items("/api/masters/equipment-models")}
    trades = {t["name"]: t["id"] for t in items("/api/masters/trades")}
    mtypes = {t["name"]: t["id"] for t in items("/api/masters/meter-types")}
    RUN, OIL = mtypes["Run hours"], mtypes["Oil temperature"]

    # Model meters
    for designation, meters in (("GA37", [(RUN, {})]),
                                ("VAH 600", [(RUN, {}), (OIL, {"min_value": "20", "max_value": "80"})]),
                                ("Generic vertical blade mill", [(RUN, {})]),
                                ("SMTW-HYP-01", [(RUN, {}), (OIL, {"min_value": "30", "max_value": "60"})]),
                                ("Generic bore pump", [(RUN, {})])):
        for type_id, limits in meters:
            api("admin", "POST", f"/api/masters/equipment-models/{models[designation]}/meters",
                {"meter_type_id": type_id, **limits})

    # Rename the e2e seed's machines to plant names
    listing = api("admin", "GET", "/api/equipment?level=all&include_scrapped=1&per_page=100")
    eq = {e["name"]: e for e in listing["items"]}
    renames = {"E2E extruder": "Main extruder", "E2E extruder gearbox": "Extruder main gearbox",
               "E2E MCC1 mill": "Blade mill 2",
               "E2E filter pump": "Bore well pump"}
    nodes = {}
    for old, new in renames.items():
        api("admin", "PUT", f"/api/equipment/{eq[old]['id']}", {"name": new})
        nodes[new] = eq[old]
    for unit, model, name, crit in (("SMTW.MCC2", "GA37", "Screw compressor 1", "A"),
                                     ("SMTW.MCC2", "GA37", "Screw compressor 2", "B"),
                                     ("SMTW.FWMILL", "Generic vertical blade mill", "Vertical blade mill", "B"),
                                     ("SMTW.MCC1", "SMTW-HYP-01", "Hydraulic press 1", "A")):
        nodes[name] = api("admin", "POST", "/api/equipment/", {"level": "equipment", "unit_id": units[unit],
                                                               "model_id": models[model], "name": name,
                                                               "criticality": crit})
    ids = {k: v["id"] for k, v in nodes.items()}

    # Readings over the last 6 days (the operator in MCC2; admin elsewhere)
    series = {"Main extruder": (11820, 21), "Screw compressor 1": (6120, 20), "Screw compressor 2": (4310, 18),
              "Vertical blade mill": (2405, 9), "Hydraulic press 1": (8810, 16)}
    for name, (start, per_day) in series.items():
        who = "operator" if name in ("Main extruder", "Screw compressor 1", "Screw compressor 2") else "admin"
        for d in range(6, 0, -1):
            minutes = d * 24 * 60 + 60 * 2
            api(who, "POST", f"/api/equipment/{ids[name]}/readings",
                {"meter_type_id": RUN, "value": str(start + (6 - d) * per_day), "taken_at": ago(minutes)})
    for d, v in ((5, "54"), (3, "57"), (2, "61"), (1, "58")):
        api("operator", "POST", f"/api/equipment/{ids['Main extruder']}/readings",
            {"meter_type_id": OIL, "value": v, "taken_at": ago(d * 1440 + 100)})
    api("admin", "POST", f"/api/equipment/{ids['Hydraulic press 1']}/readings",
        {"meter_type_id": OIL, "value": "47", "taken_at": ago(1440 + 150)})

    vendor = api("admin", "POST", "/api/masters/vendors", {"name": "Atlas Copco service", "phone": "98400 00000",
                                                           "note": "Authorised service for GA compressors"})
    vtech = api("admin", "POST", "/api/masters/people",
                {"name": "Atlas Copco service engineer", "employment": "contractor",
                 "vendor_id": vendor["id"], "trade_ids": [trades["Mechanical"]]})
    site_ids = {x["code"]: x["id"] for x in items("/api/masters/sites")}
    api("admin", "PUT", f"/api/masters/people/{vtech['id']}/sites/{site_ids['SMTW']}",
        {"role": "maint_technician", "all_units": True, "unit_ids": []})

    # Tickets
    def raise_(who, body):
        return api(who, "POST", "/api/tickets", body)

    def move(who, t, name, body=None):
        return api(who, "POST", f"/api/tickets/{t['id']}/moves/{name}", body or {})

    t_new = raise_("operator", {"equipment_id": ids["Main extruder"], "intensity": "degraded",
                                "failure_mode_id": 9, "occurred_at": ago(40),
                                "description": "Vacuum pump not reaching -0.9 bar. Bricks show small cracks."})
    t_ack = raise_("operator", {"equipment_id": ids["Extruder main gearbox"], "intensity": "degraded",
                                "failure_mode_id": 5, "occurred_at": ago(300),
                                "description": "Gearbox oil leak at output seal. A small pool under the gearbox."})
    move("technician", t_ack, "acknowledge", {"occurred_at": ago(270)})
    api("engineer", "POST", f"/api/tickets/{t_ack['id']}/assignees", {"person_id": me["technician2"]})
    t_prog = raise_("operator", {"equipment_id": ids["Screw compressor 1"], "intensity": "critical",
                                 "failure_mode_id": 8, "occurred_at": ago(95),
                                 "description": "Compressor tripping on high temperature. Display shows 110 °C."})
    move("technician", t_prog, "start", {"occurred_at": ago(80)})
    api("engineer", "POST", f"/api/tickets/{t_prog['id']}/assignees", {"person_id": vtech["id"]})
    api("technician", "POST", f"/api/tickets/{t_prog['id']}/notes",
        {"remark": "Cooler fins blocked with clay dust. Cleaning with air now."})
    t_bis = raise_("supervisor", {"equipment_id": ids["Blade mill 2"], "intensity": "degraded", "failure_mode_id": 7,
                                  "occurred_at": ago(1500), "description": "Blade mill 2 vibrating at the drive end."})
    move("technician", t_bis, "start", {"occurred_at": ago(1440)})
    api("technician", "POST", f"/api/tickets/{t_bis['id']}/labour",
        {"person_id": me["technician"], "trade_id": trades["Mechanical"], "work_date": day(-1), "minutes": 90})
    move("technician", t_bis, "restore", {"person_id": me["technician"], "occurred_at": ago(1350)})
    t_closed = raise_("operator", {"equipment_id": ids["Screw compressor 2"], "intensity": "degraded",
                                   "failure_mode_id": 6, "occurred_at": ago(2900),
                                   "description": "Squealing noise from the cooling fan belt."})
    move("technician2", t_closed, "start", {"occurred_at": ago(2850)})
    move("technician2", t_closed, "restore", {"person_id": me["technician2"], "occurred_at": ago(2790)})
    api("technician2", "POST", f"/api/tickets/{t_closed['id']}/labour",
        {"person_id": me["technician2"], "trade_id": trades["Electrical"], "work_date": day(-2), "minutes": 45})
    move("engineer", t_closed, "close", {"cause_id": 8, "action_id": 1, "failure_mode_id": 6,
                                          "remark": "Belt worn. Fitted a new belt."})
    t_sched = raise_("operator", {"equipment_id": ids["Main extruder"], "intensity": "initial",
                                  "failure_mode_id": 13, "occurred_at": ago(600),
                                  "description": "Die heater cable loose at the terminal box."})
    move("engineer", t_sched, "schedule", {"planned_date": day(2), "waiting_reason": "slot"})

    # A breakdown three days ago, fixed: the improvement's ticket
    t_fix = raise_("engineer", {"equipment_id": ids["Screw compressor 1"], "intensity": "critical",
                                "failure_mode_id": 8, "occurred_at": ago(3 * 1440 + 120),
                                "description": "Compressor 1 stopped on high temperature trip.",
                                "restore": {"person_id": me["technician"], "occurred_at": ago(3 * 1440 + 30)}})
    api("technician", "POST", f"/api/tickets/{t_fix['id']}/labour",
        {"person_id": me["technician"], "trade_id": trades["Mechanical"], "work_date": day(-3), "minutes": 75})
    api("technician", "POST", f"/api/tickets/{t_fix['id']}/labour",
        {"person_id": vtech["id"], "trade_id": trades["Mechanical"], "work_date": day(-3), "minutes": 60})
    move("engineer", t_fix, "close", {"cause_id": 8, "action_id": 7, "failure_mode_id": 8,
                                       "remark": "Cleaned the oil cooler. Back in service."})

    # Improvement
    imp = api("engineer", "POST", "/api/improvements", {
        "ticket_id": t_fix["id"], "title": "Compressor 1 trips on high temperature",
        "problem": "Screw compressor 1 stopped twice this month on the high temperature trip. "
                   "Each stop held the extruder line for about an hour.", "lead_id": me["engineer"]})
    api("engineer", "POST", f"/api/improvements/{imp['id']}/tickets", {"ticket_id": t_prog["id"]})
    for q, a in (("Why did the compressor trip?", "The oil temperature went above 110 °C."),
                 ("Why did the oil get so hot?", "The oil cooler could not shed the heat."),
                 ("Why could the cooler not shed the heat?", "Its fins were blocked with clay dust."),
                 ("Why were the fins blocked?", "Nobody cleans the cooler; it is not on any checklist.")):
        api("engineer", "POST", f"/api/improvements/{imp['id']}/whys", {"question": q, "answer": a})
    api("engineer", "PUT", f"/api/improvements/{imp['id']}/root-cause", {
        "root_cause": "Cooler cleaning is not part of the weekly compressor check.", "root_cause_id": 10,
        "contributing_causes": "The compressor room takes clay dust from the extruder line."})
    owners = {p["name"]: p["id"] for p in items(f"/api/improvements/owners?improvement_id={imp['id']}", "engineer")}
    a1 = api("engineer", "POST", f"/api/improvements/{imp['id']}/actions", {
        "kind": "correction", "text": "Clean the oil cooler fins on both compressors",
        "owner_id": owners["Kannan"], "due_date": day(0)})["actions"][-1]
    api("technician", "POST", f"/api/improvements/{imp['id']}/actions/{a1['id']}/done",
        {"done_text": "Both coolers cleaned with compressed air."})
    api("engineer", "POST", f"/api/improvements/{imp['id']}/actions", {
        "kind": "preventive", "text": "Add 'Clean the cooler fins' to the weekly compressor PM plan",
        "owner_id": owners["Priya"], "due_date": day(7)})
    api("engineer", "POST", f"/api/improvements/{imp['id']}/actions", {
        "kind": "design_out", "text": "Fit a dust filter on the compressor room air inlet",
        "owner_id": owners["Ravi"], "due_date": day(21)})

    # One-point lesson
    lesson = api("engineer", "POST", "/api/procedures", {
        "equipment_id": ids["Screw compressor 1"], "title": "Check the oil level before you start the compressor",
        "body": "1. Stop the compressor and wait 5 minutes.\n2. Look at the sight glass on the oil separator.\n"
                "3. The oil must be between the two marks.\n4. Low oil? Do not start. Call the technician.",
        "for_class": True})
    upload("engineer", f"/api/procedures/{lesson['id']}/documents",
           {"kind": "photo", "title": "Oil sight glass"}, PHOTO)

    # Vendor and contract
    contract = api("manager", "POST", "/api/contracts", {
        "vendor_id": vendor["id"], "contract_type": "amc", "title": "AMC for the screw compressors",
        "contract_number": "AMC-2026-014", "from_date": day(-240), "to_date": day(45),
        "covers_labour": True, "covers_parts": False, "covers_consumables": True, "covers_breakdown_calls": True,
        "breakdown_calls_per_year": 4, "pm_visits_per_year": 4, "response_hours": 24,
        "covered_text": "Quarterly service visit, oil and filters, breakdown visits.",
        "not_covered_text": "Air-end overhaul, motor rewinding.", "callout_number": "1800 000 0000",
        "cost_note": "Quoted per machine; parts at 10 % discount."})
    for name, price in (("Screw compressor 1", "48000"), ("Screw compressor 2", "48000")):
        api("manager", "POST", f"/api/contracts/{contract['id']}/equipment",
            {"equipment_id": ids[name], "price": price})

    # PM plans
    def plan(name, title, *, kind="calendar", every=None, unit=None, meter_every=None, last_on=None,
             last_meter=None, plan_items, verify=True, who="engineer", assignee="technician"):
        body = {"equipment_id": ids[name], "title": title, "trigger_kind": kind, "assignee_id": me[assignee],
                "needs_verification": verify, "items": plan_items, "last_done_on": last_on}
        if kind in ("calendar", "both"):
            body.update(calendar_every=every, calendar_unit=unit)
        if kind in ("meter", "both"):
            body.update(meter_every=str(meter_every), meter_type_id=RUN, meter_equipment_id=ids[name],
                        last_done_meter=str(last_meter))
        return api(who, "POST", "/api/pm/plans", body)

    def job_of(p):
        for tab in ("due", "upcoming"):
            for j in items(f"/api/pm/jobs?tab={tab}", "engineer"):
                if j["plan"]["id"] == p["id"]:
                    return j
        return None

    def start(job, who="technician"):
        return api(who, "POST", f"/api/pm/jobs/{job['id']}/start", {"performed_by_id": me[who], "started_at": None})

    def fill(job, started, answers):
        for item, ans in zip(started["items"], answers):
            if ans is not None:
                api("technician", "PUT", f"/api/pm/jobs/{job['id']}/results/{item['id']}", ans)

    ext_items = [
        {"item_type": "check", "text": "No oil leaks at the gearbox", "photo": "optional"},
        {"item_type": "check", "text": "Vacuum gauge reads -0.9 bar or better", "photo": "none"},
        {"item_type": "task", "text": "Grease the auger shaft bearings", "photo": "none",
         "help_text": "Two shots of EP2 grease at each nipple."},
        {"item_type": "reading", "text": "Gearbox oil temperature", "photo": "none", "meter_type_id": OIL,
         "meter_equipment_id": ids["Main extruder"], "min_value": "20", "max_value": "80"},
    ]
    p_ext = plan("Main extruder", "Weekly extruder check", every=1, unit="week", last_on=day(-9), plan_items=ext_items)
    comp_items = [
        {"item_type": "task", "text": "Clean the oil cooler fins with compressed air", "photo": "optional"},
        {"item_type": "task", "text": "Change the air filter element", "photo": "none"},
        {"item_type": "check", "text": "Oil level between the marks in the sight glass", "photo": "none"},
        {"item_type": "reading", "text": "Discharge temperature at full load", "photo": "none", "unit": "°C",
         "min_value": "70", "max_value": "100"},
    ]
    p_c1 = plan("Screw compressor 1", "500-hour compressor service", kind="both", every=3, unit="month",
                meter_every=500, last_on=day(-80), last_meter=5730, plan_items=comp_items)
    j = job_of(p_c1)
    st = start(j)
    fill(j, st, [{"outcome": "done"}, {"outcome": "done"}, None, None])

    p_c2 = plan("Screw compressor 2", "Monthly compressor check", every=1, unit="month", last_on=day(-33),
                plan_items=[{"item_type": "check", "text": "No air leaks at the hoses and joints", "photo": "none"},
                            {"item_type": "check", "text": "Drain valve works; no water in the receiver",
                             "photo": "none"},
                            {"item_type": "task", "text": "Clean the oil cooler fins", "photo": "none"},
                            {"item_type": "reading", "text": "Discharge temperature at full load", "photo": "none",
                             "unit": "°C", "min_value": "70", "max_value": "100"}])
    j = job_of(p_c2)
    st = start(j, "technician2")
    hiss = {"outcome": "not_ok", "remark": "Hose joint at the dryer hisses. Clamp is loose."}
    for item, ans in zip(st["items"], [hiss,
                                       {"outcome": "ok"}, {"outcome": "done"}, {"value": "92.5"}]):
        api("technician2", "PUT", f"/api/pm/jobs/{j['id']}/results/{item['id']}", ans)
    api("technician2", "POST", f"/api/pm/jobs/{j['id']}/done", {})

    mill_items = [{"item_type": "check", "text": "Blades sharp, no broken teeth", "photo": "optional"},
                  {"item_type": "check", "text": "Guard fitted and bolts tight", "photo": "none"},
                  {"item_type": "task", "text": "Grease the main shaft bearings", "photo": "none"}]
    p_mill = plan("Vertical blade mill", "Weekly blade mill check", every=1, unit="week", last_on=day(-8),
                  plan_items=mill_items)
    j = job_of(p_mill)
    st = start(j)
    fill(j, st, [{"outcome": "ok"}, {"outcome": "ok"}, {"outcome": "done"}])
    api("technician", "POST", f"/api/pm/jobs/{j['id']}/done", {})
    api("engineer", "POST", f"/api/pm/jobs/{j['id']}/verify", {"remark": "Checked the blades myself. Good."})

    p_press = plan("Hydraulic press 1", "Hydraulic press check", every=10, unit="day", last_on=day(-10),
                   plan_items=[{"item_type": "check", "text": "No oil leaks at the cylinder seals",
                                "photo": "optional"},
                               {"item_type": "check", "text": "Safety light curtain stops the ram", "photo": "none"},
                               {"item_type": "reading", "text": "Power-pack oil temperature", "photo": "none",
                                "meter_type_id": OIL, "meter_equipment_id": ids["Hydraulic press 1"],
                                "min_value": "30", "max_value": "60"}])
    p_gbx = plan("Extruder main gearbox", "Gearbox oil change", every=6, unit="month", last_on=day(-178),
                 plan_items=[{"item_type": "task", "text": "Drain and refill gearbox oil (ISO VG 320, 40 L)",
                              "photo": "optional"},
                             {"item_type": "check", "text": "Magnetic plug clean, no metal chips", "photo": "none"}])
    p_back = plan("Main extruder", "Monthly vacuum pump service", every=1, unit="month", last_on=day(-32),
                  plan_items=[{"item_type": "task", "text": "Change the vacuum pump oil", "photo": "none"},
                              {"item_type": "check", "text": "Pump belt tension OK", "photo": "none"}])
    j = job_of(p_back)
    st = start(j)
    fill(j, st, [{"outcome": "done"}, {"outcome": "ok"}])
    api("technician", "POST", f"/api/pm/jobs/{j['id']}/done", {})
    api("engineer", "POST", f"/api/pm/jobs/{j['id']}/send-back",
        {"remark": "Belt is still loose. Tighten it and check again."})
    p_skip = plan("Blade mill 2", "Monthly blade mill lubrication", every=1, unit="month", last_on=day(-31),
                  plan_items=[{"item_type": "task", "text": "Grease the shaft bearings", "photo": "none"}])
    j = job_of(p_skip)
    api("engineer", "POST", f"/api/pm/jobs/{j['id']}/skip",
        {"remark": "Blade mill 2 stopped all month for the line change."})

    out = {"ids": ids, "codes": {k: v.get("code") for k, v in nodes.items()},
           "tickets": {"new": t_new["id"], "ack": t_ack["id"], "prog": t_prog["id"], "bis": t_bis["id"],
                       "closed": t_closed["id"], "sched": t_sched["id"], "fix": t_fix["id"]},
           "improvement": imp["id"], "lesson": lesson["id"], "contract": contract["id"],
           "plans": {"ext": p_ext["id"], "c1": p_c1["id"], "c2": p_c2["id"], "mill": p_mill["id"],
                     "press": p_press["id"], "gbx": p_gbx["id"], "back": p_back["id"], "skip": p_skip["id"]}}
    jobs = {}
    for tab in ("due", "upcoming", "to_verify", "done"):
        for jj in items(f"/api/pm/jobs?tab={tab}", "engineer"):
            jobs.setdefault(jj["plan"]["id"], jj["id"])
    out["jobs"] = {k: jobs.get(v) for k, v in out["plans"].items()}
    (OUT / "data.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
