"""The PM tests' shared set-up (S104 § 8.3): the fixtures (a site, an engineer, meter types, a press with model
meters), a template body, and ``plan_on``: a template linked to one node, returning the machine's plan.

Since S104 a machine gets a plan only through a template.  The S097–S102 tests were written against S096's plan
body (a title, a trigger with a meter node, items, an assignee and *Last done* in one request), so ``create`` and
``change`` keep that call shape: they split the body into the template's fields (POST / PUT /api/pm/templates) and
the plan row's (PUT /api/pm/plans/<id>), and answer the plan's detail with ``items`` (the template's items) beside
it, the test-only shortcut the old tests read.  A template name is unique in the whole test database, kept for the
session, so every name gets a number (" #12") unless it has one.
"""

import itertools
import re

import pytest

PM = "/api/pm"
PLANS = f"{PM}/plans"
TEMPLATES = f"{PM}/templates"
MASTERS = "/api/masters"
EQUIPMENT = "/api/equipment"
SCRAPPED = "This record is scrapped and cannot be changed"
CHECK = {"item_type": "check", "text": "Oil level in the sight glass is above min"}
TASK = {"item_type": "task", "text": "Grease the main bearing"}
TITLE = "Monthly hydraulic check"

# The plan row's own fields (pm_plans_core.PLAN_FIELDS); every other field of an old plan body is the template's
PLAN_FIELDS = ("assignee_id", "last_done_on", "last_done_meter")
_numbers = itertools.count(1)
_NUMBERED = re.compile(r" #\d+$")


def _ok(res, status=200):
    assert res.status_code == status, res.get_json()
    return res.get_json()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def site(unit):
    return {"id": unit["site_id"]}


@pytest.fixture
def other_site(make_site):
    return make_site()


@pytest.fixture
def other_unit(make_unit, other_site):
    return make_unit(site=other_site)


@pytest.fixture
def eng(user_at_sites, site):
    """(client, person): an engineer with all units of the machine's site."""
    return user_at_sites([(site, "maint_engineer", "all")])


@pytest.fixture
def engineer_a(eng):
    return eng[0]


@pytest.fixture
def at_site(user_at_sites, site):
    """at_site(role) -> a client holding that role at every unit of the machine's site."""
    return lambda role: user_at_sites([(site, role, "all")])[0]


@pytest.fixture
def hours(make_meter_type):
    return make_meter_type(unit="h", kind="counter", decimals=1)


@pytest.fixture
def oil(make_meter_type):
    return make_meter_type()


@pytest.fixture
def add_model_meter(admin):
    def add(node, meter_type, **limits):
        _ok(admin.post(f"{MASTERS}/equipment-models/{node['model_id']}/meters",
                       json={"meter_type_id": meter_type["id"], **limits}), 201)
    return add


@pytest.fixture
def add_own_meter(admin):
    def add(node, meter_type):
        _ok(admin.post(f"{EQUIPMENT}/{node['id']}/meters", json={"meter_type_id": meter_type["id"]}), 201)
    return add


@pytest.fixture
def press(machine, hours, oil, add_model_meter):
    """The machine with two model meters: run hours (a counter) and oil temperature (a gauge, 20–70 °C)."""
    add_model_meter(machine, hours)
    add_model_meter(machine, oil, min_value="20", max_value="70")
    return machine


@pytest.fixture
def technician(make_person, give_site_role, site):
    """A technician at every unit of the machine's site (an assignable person, no login)."""
    person = make_person(name="Ravi")
    give_site_role(person, site, "maint_technician")
    return person


@pytest.fixture
def tech(user_at_sites, site):
    """(client, person): a technician with a login at every unit of the machine's site."""
    return user_at_sites([(site, "maint_technician", "all")])


# ---------------------------------------------------------------------------
# Templates and plans
# ---------------------------------------------------------------------------

def unique(name):
    """``name`` with a number, unless it has one: template names are unique in the whole database."""
    return name if _NUMBERED.search(name) else f"{name} #{next(_numbers)}"


def template_body(**fields):
    """A calendar template, every month, a Check and a Task, under a fresh name."""
    return {"name": unique(fields.pop("name", TITLE)), "trigger_kind": "calendar", "calendar_every": 1,
            "calendar_unit": "month", "items": [CHECK, TASK], **fields}


def make_template(client, status=201, **fields):
    return _ok(client.post(TEMPLATES, json=template_body(**fields)), status)


def change_template(client, template, status=200, **fields):
    return _ok(client.put(f"{TEMPLATES}/{template['id']}", json=fields), status)


def attach(client, node, template, status=201):
    return _ok(client.post(PLANS, json={"equipment_id": node["id"], "template_id": template["id"]}), status)


def plan_of(client, plan_id):
    """The plan's detail, with the template's items beside it as ``items`` (the old tests read them there)."""
    plan = _ok(client.get(f"{PLANS}/{plan_id}"))
    return {**plan, "items": plan["template"]["items"]}


def link_meter(client, part, source, meter_type, status=201):
    """S104 A1: ``part`` uses ``source``'s meter of ``meter_type`` (*Use a meter from above*) -> the part's meters.
    A link already there (the same part and type) is left as it is."""
    res = client.post(f"{EQUIPMENT}/{part['id']}/meter-links",
                      json={"meter_type_id": meter_type["id"], "source_equipment_id": source["id"]})
    if status == 201 and res.status_code == 409 and "already uses" in res.get_json()["error"]:
        return res.get_json()
    return _ok(res, status)


def unlink_meter(client, part, meter_type, status=200):
    return _ok(client.delete(f"{EQUIPMENT}/{part['id']}/meter-links/{meter_type['id']}"), status)


def _template_item(item, links, node_id):
    """An S096-shaped item (a meter named by node and type, or a unit and limits) -> the template's shape (§ 5.2): a
    reading with a meter is a *Meter reading* (its own limits dropped, D6), a reading without one a *Measurement*.
    A meter of another node than ``node_id`` is added to ``links`` ({meter_type_id: node id}): S104 A1 sets a
    meter link on the part where S096 named the parent's meter."""
    out = {key: value for key, value in item.items() if key not in ("meter_equipment_id", "meter", "limits_text",
                                                                     "position")}
    if item.get("item_type") != "reading" or "reading_kind" in item:
        return out
    meter_node = item.get("meter_equipment_id")
    if item.get("meter_type_id") is None:
        return {**out, "reading_kind": "measurement"}
    if meter_node is not None and meter_node != node_id:
        links[item["meter_type_id"]] = meter_node
    out.update(reading_kind="meter", unit=None, min_value=None, max_value=None)
    return out


def _split(node_id, fields):
    """An old plan body -> (template fields, plan fields, links: {meter_type_id: the node whose meter it is})."""
    template, plan, links = {}, {}, {}
    for key, value in fields.items():
        if key in PLAN_FIELDS:
            plan[key] = value
        elif key == "title":
            template["name"] = value
        elif key == "meter_equipment_id":
            if value is not None and value != node_id:
                links[fields["meter_type_id"]] = value
        elif key == "items":
            template["items"] = [_template_item(item, links, node_id) for item in value]
        elif key not in ("equipment_id",):
            template[key] = value
    return template, plan, links


def _link_all(client, node, links):
    for meter_type_id, source_id in links.items():
        link_meter(client, node, {"id": source_id}, {"id": meter_type_id})


def plan_on(client, node, status=201, **fields):
    """A template made of ``fields`` (an S096-shaped body: title, trigger, meter, items, …) and attached to ``node``,
    then the plan row's own fields (assignee, Last done) set -> the plan's detail (``items`` beside it).  ``status``
    is the template POST's; a refused template answers its body.  A meter named on another node than ``node`` is
    linked on ``node`` first (S104 A1)."""
    template_fields, plan_fields, links = _split(node["id"], fields)
    res = client.post(TEMPLATES, json=template_body(**template_fields))
    if status != 201:
        return _ok(res, status)
    template = _ok(res, 201)
    _link_all(client, node, links)
    plan = attach(client, node, template)
    if plan_fields:
        _ok(client.put(f"{PLANS}/{plan['id']}", json=plan_fields))
    return plan_of(client, plan["id"])


create = plan_on   # the S097–S102 tests' name


def change(client, plan, status=200, **fields):
    """An S096-shaped change of a plan: the template's fields go to its template (``active`` too: a deactivation
    stops every machine of the template), the plan row's to the plan -> the plan's detail."""
    template_fields, plan_fields, links = _split(plan["equipment"]["id"], fields)
    _link_all(client, plan["equipment"], links)
    if "name" in template_fields and template_fields["name"] != plan["title"]:
        template_fields["name"] = unique(template_fields["name"])
    if template_fields:
        res = client.put(f"{TEMPLATES}/{plan['template']['id']}", json=template_fields)
        if status != 200:
            return _ok(res, status)
        _ok(res)
    if plan_fields:
        res = client.put(f"{PLANS}/{plan['id']}", json=plan_fields)
        if status != 200:
            return _ok(res, status)
        _ok(res)
    return plan_of(client, plan["id"])


def meter_of(node, meter_type):
    """S096's meter pair; ``plan_on`` turns it into the template's meter type (and a meter link on the part when the
    node is another one, S104 A1)."""
    return {"meter_equipment_id": node["id"], "meter_type_id": meter_type["id"]}


def item_body(item):
    """A template item of the answer as the template page sends it back."""
    return {"id": item["id"], "item_type": item["item_type"], "text": item["text"], "help_text": item["help_text"],
            "photo": item["photo"], "reading_kind": item["reading_kind"], "unit": item["unit"],
            "min_value": item["min_value"], "max_value": item["max_value"],
            "meter_type_id": item["meter_type"] and item["meter_type"]["id"]}
