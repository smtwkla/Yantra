"""v57, PM's whole shape in one migration (S104 § 4.1, § 8.1), in the upgrade database UPGRADE_DB (one per test run
and worker, tests/db_names.py), dropped and created by these tests.

- a fresh build: every table, key, foreign key and CHECK of § 4.1; a CHECK refuses a bad row each; one active link
  per template and target, removed links pile up;
- a database at v56 with rows (built from the frozen migrations_v56.py): v57 drops the five PM tables and makes the
  final shape a fresh database gets; db_version keeps v51–v56 and gains v57;
- a re-run of v57 changes nothing;
- the ENUMs equal the code's vocabularies (S096's pin, moved to the template).

Needs the dev MariaDB container.
"""

import pymysql
import pytest

import local_db
from pm_links_core import TARGET_KINDS
from pm_schedule_core import CALENDAR_UNITS, KINDS
from pm_templates_core import READING_KINDS
from tests.fixtures.migrations_v56 import MIGRATIONS_V51_V56
from tests.migration_helpers import _migrate, _recreate, _run, _schema, _versions
from tests.test_migration_v22 import _fill_one_ticket
from tests.test_migration_v36 import _foreign_keys, _keys

V50 = [m for m in local_db._MIGRATIONS if m[0] <= 50]
V57 = [m for m in local_db._MIGRATIONS if m[0] <= 57]

ER_CONSTRAINT_FAILED = 4025
ER_DUP_ENTRY = 1062
PM_TABLES = ["pm_job_events", "pm_job_results", "pm_jobs", "pm_plans", "pm_template_items", "pm_template_links",
             "pm_templates"]


def _insert(table, row):
    _run(f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join(['%s'] * len(row))})", list(row.values()))
    return _run(f"SELECT MAX(id) AS id FROM {table}")[0]["id"]


def _enum(table, column):
    column_type = _run("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()"
                       " AND TABLE_NAME = %s AND COLUMN_NAME = %s", (table, column))[0]["COLUMN_TYPE"]
    return tuple(value.strip("'") for value in column_type.removeprefix("enum(").removesuffix(")").split(","))


def _checks(table):
    return sorted(r["CONSTRAINT_NAME"] for r in _run(
        "SELECT CONSTRAINT_NAME FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()"
        " AND TABLE_NAME = %s", (table,)))


def _refused(code, table, row):
    with pytest.raises((pymysql.err.OperationalError, pymysql.err.IntegrityError)) as refused:
        _insert(table, row)
    assert refused.value.args[0] == code, refused.value


_names = iter(range(1, 100_000))


def _ids():
    return {"equipment_id": _run("SELECT id FROM equipment WHERE code = 'HP001'")[0]["id"],
            "meter_type_id": _run("SELECT id FROM meter_types ORDER BY id LIMIT 1")[0]["id"]}


def _template(**fields):
    return _insert("pm_templates", {"name": f"Template {next(_names)}", "trigger_kind": "calendar",
                                    "calendar_every": 1, "calendar_unit": "month", "created_by": "kla", **fields})


def _link(template_id, **fields):
    return _insert("pm_template_links", {"template_id": template_id, "target_kind": "equipment",
                                         "equipment_id": _ids()["equipment_id"], "created_by": "kla", **fields})


@pytest.fixture(scope="module")
def fresh():
    _recreate()
    _migrate(V57)
    _fill_one_ticket()
    return _schema()


def test_the_tables_keys_and_foreign_keys(fresh):
    # Sorted in Python: the collation orders "_" against letters differently from PM_TABLES.
    tables = sorted(r["TABLE_NAME"] for r in _run("SELECT TABLE_NAME FROM information_schema.TABLES"
                                                  " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE %s",
                                                  ("pm\\_%",)))
    assert tables == sorted(PM_TABLES)
    keys = {k["INDEX_NAME"]: k["cols"] for table in PM_TABLES for k in _keys(table)}
    assert keys["uq_pm_templates_name"] == "name"
    assert keys["ix_pm_template_items_template"] == "template_id,active,position"
    assert keys["uq_pm_template_links_open"] == "template_id,target_kind,open_target_id"
    assert keys["ix_pm_template_links_target"] == "target_kind,target_id,active"
    assert keys["uq_pm_plans_template"] == "equipment_id,template_id"
    assert keys["uq_pm_jobs_open_plan"] == "open_plan_id"
    assert keys["uq_pm_job_results_item"] == "job_id,template_item_id"
    assert [(f["CONSTRAINT_NAME"], f["REFERENCED_TABLE_NAME"]) for f in _foreign_keys("pm_plans")] == [
        ("fk_pm_plans_assignee", "people"), ("fk_pm_plans_equipment", "equipment"),
        ("fk_pm_plans_seed_meter_equipment", "equipment"), ("fk_pm_plans_seed_meter_type", "meter_types"),
        ("fk_pm_plans_template", "pm_templates")]
    assert ("fk_pm_jobs_meter_equipment", "equipment") in [
        (f["CONSTRAINT_NAME"], f["REFERENCED_TABLE_NAME"]) for f in _foreign_keys("pm_jobs")]
    assert ("fk_pm_job_results_item", "pm_template_items") in [
        (f["CONSTRAINT_NAME"], f["REFERENCED_TABLE_NAME"]) for f in _foreign_keys("pm_job_results")]
    assert _checks("pm_template_items") == ["chk_pm_template_items_kind", "chk_pm_template_items_limits",
                                            "chk_pm_template_items_position", "chk_pm_template_items_reading"]
    assert _checks("pm_template_links") == ["chk_pm_template_links_removed", "chk_pm_template_links_target"]
    assert _checks("pm_plans") == ["chk_pm_plans_not_for", "chk_pm_plans_seed"]
    assert _checks("pm_templates") == ["chk_pm_templates_calendar", "chk_pm_templates_meter"]


def test_the_plan_row_holds_no_work(fresh):
    columns = {r["COLUMN_NAME"] for r in _run("SELECT COLUMN_NAME FROM information_schema.COLUMNS"
                                              " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'pm_plans'")}
    assert not columns & {"title", "trigger_kind", "performer", "needs_verification", "meter_equipment_id",
                          "meter_type_id", "active"}
    assert {"linked", "linked_at", "not_for_machine", "seed_meter_equipment_id", "seed_meter_type_id"} <= columns


def test_the_enums_equal_the_code(fresh):
    assert _enum("pm_templates", "trigger_kind") == KINDS
    assert _enum("pm_templates", "calendar_unit") == CALENDAR_UNITS
    assert _enum("pm_template_items", "reading_kind") == READING_KINDS
    assert _enum("pm_job_results", "reading_kind") == READING_KINDS
    assert _enum("pm_template_links", "target_kind") == TARGET_KINDS


def test_a_check_refuses_a_bad_row_each(fresh):
    ids = _ids()
    template_id = _template()
    item = {"template_id": template_id, "position": 1, "item_type": "reading", "text": "Oil", "created_by": "kla"}
    _refused(ER_CONSTRAINT_FAILED, "pm_template_items",
             {**item, "reading_kind": "measurement", "meter_type_id": ids["meter_type_id"]})
    _refused(ER_CONSTRAINT_FAILED, "pm_template_items", {**item, "reading_kind": "meter", "unit": "°C",
                                                         "meter_type_id": ids["meter_type_id"]})
    _refused(ER_CONSTRAINT_FAILED, "pm_template_items", item)   # a reading without its kind
    _insert("pm_template_items", {**item, "reading_kind": "meter", "meter_type_id": ids["meter_type_id"],
                                  "meter_from_parent": 1})
    model_id = _run("SELECT id FROM equipment_models LIMIT 1")[0]["id"]
    _refused(ER_CONSTRAINT_FAILED, "pm_template_links", {"template_id": template_id, "target_kind": "equipment",
                                                         "model_id": model_id, "created_by": "kla"})
    _refused(ER_CONSTRAINT_FAILED, "pm_plans", {"equipment_id": ids["equipment_id"], "template_id": template_id,
                                                "not_for_machine": 1, "created_by": "kla"})
    _refused(ER_CONSTRAINT_FAILED, "pm_plans", {"equipment_id": ids["equipment_id"], "template_id": template_id,
                                                "last_done_meter": 10, "created_by": "kla"})
    _refused(ER_CONSTRAINT_FAILED, "pm_templates", {"name": "Tick", "trigger_kind": "calendar", "calendar_every": 1,
                                                    "calendar_unit": "month", "meter_from_parent": 1,
                                                    "created_by": "kla"})


def test_one_active_link_per_template_and_node(fresh):
    template_id = _template()
    first = _link(template_id)
    _refused(ER_DUP_ENTRY, "pm_template_links", {"template_id": template_id, "target_kind": "equipment",
                                                 "equipment_id": _ids()["equipment_id"], "created_by": "kla"})
    _run("UPDATE pm_template_links SET active = 0, removed_at = NOW(), removed_by = 'kla' WHERE id = %s", (first,))
    second = _link(template_id)
    rows = _run("SELECT id, active, target_id, open_target_id FROM pm_template_links WHERE template_id = %s"
                " ORDER BY id", (template_id,))
    node = _ids()["equipment_id"]
    assert [(r["id"], r["active"], r["target_id"], r["open_target_id"]) for r in rows] == [
        (first, 0, node, None), (second, 1, node, node)]


def _fill_v56():
    """A plan with an item, a job and a result in the v56 shape (the old tables)."""
    _fill_one_ticket()
    ids = _ids()
    _run("INSERT INTO people (name, employment, created_by) VALUES ('Kannan', 'direct', 'kla')")
    person = _run("SELECT id FROM people")[0]["id"]
    plan_id = _insert("pm_plans", {"equipment_id": ids["equipment_id"], "title": "Monthly check",
                                   "trigger_kind": "calendar", "calendar_every": 1, "calendar_unit": "month",
                                   "created_by": "kla"})
    item_id = _insert("pm_plan_items", {"plan_id": plan_id, "position": 1, "item_type": "check", "text": "Oil level",
                                        "created_by": "kla"})
    job_id = _insert("pm_jobs", {"serial": "PM-2026-11-001", "plan_id": plan_id, "equipment_id": ids["equipment_id"],
                                 "state": "in_progress", "created_why": "calendar", "due_on": "2026-11-02",
                                 "grace_days": 3, "upcoming_days": 3, "performed_by_id": person,
                                 "started_at": "2026-11-02 09:00:00", "created_by": "kla"})
    _insert("pm_job_results", {"job_id": job_id, "plan_item_id": item_id, "position": 1, "item_type": "check",
                               "text": "Oil level", "photo": "optional", "created_by": "kla"})


def test_a_v56_database_with_rows_migrates(fresh):
    _recreate()
    _migrate(V50 + MIGRATIONS_V51_V56)
    _fill_v56()
    assert _versions()[-1] == 56
    _migrate(V57)
    assert _versions()[-7:] == [51, 52, 53, 54, 55, 56, 57]
    assert all(_run(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"] == 0 for table in PM_TABLES)
    assert _run("SELECT COUNT(*) AS n FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
                " AND TABLE_NAME = 'pm_plan_items'")[0]["n"] == 0
    assert _schema() == fresh


def test_a_re_run_changes_nothing(fresh):
    _recreate()
    _migrate(V57)
    _run("DELETE FROM db_version WHERE version = 57")
    _migrate(V57)
    assert _schema() == fresh
    assert _versions()[-2:] == [50, 57]
